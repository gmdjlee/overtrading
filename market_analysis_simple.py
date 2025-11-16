import logging
import time
import warnings
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from pykrx import stock

warnings.filterwarnings("ignore")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MarketIndex(Enum):
    """시장 지수 정의"""
    KOSPI = ("1001", "KOSPI", "코스피")
    KOSDAQ = ("2001", "KOSDAQ", "코스닥")
    KOSPI200 = ("1028", "KOSPI200", "코스피200")
    KOSDAQ150 = ("2203", "KOSDAQ150", "코스닥150")

    def __init__(self, ticker: str, name: str, korean_name: str):
        self.ticker = ticker
        self.display_name = name
        self.korean_name = korean_name


@dataclass
class MarketConfig:
    """시장 데이터 수집 설정"""
    start_date: str
    end_date: str
    api_delay: float = 0.1  # API 호출 간 대기 시간

    def __post_init__(self):
        """설정 검증"""
        if self.start_date > self.end_date:
            raise ValueError("시작일이 종료일보다 늦을 수 없습니다")


class StockDataCollector:
    """주식 데이터 수집"""

    def __init__(self, config: MarketConfig):
        self.config = config

    def collect_index_data(self, indices: List[MarketIndex]) -> Dict[str, pd.DataFrame]:
        """지수 데이터 수집"""
        logger.info("지수 데이터 수집 시작")
        index_data = {}

        for index in indices:
            logger.info(f"{index.display_name} 데이터 수집 중...")

            try:
                df = stock.get_index_ohlcv(
                    self.config.start_date,
                    self.config.end_date,
                    index.ticker
                )

                if df.empty:
                    logger.warning(f"{index.display_name} 데이터가 없습니다")
                    continue

                # 필요한 컬럼만 선택
                df = df[["종가", "거래량"]].reset_index()
                df.columns = ["날짜", "종가", "거래량"]

                index_data[index.display_name] = df
                logger.info(f"{index.display_name}: {len(df)}개 데이터 수집 완료")

                time.sleep(self.config.api_delay)

            except Exception as e:
                logger.error(f"{index.display_name} 수집 실패: {e}")
                continue

        return index_data

    def get_index_components(self, index: MarketIndex) -> List[str]:
        """지수 구성 종목 조회"""
        logger.info(f"{index.display_name} 구성 종목 조회")

        try:
            tickers = stock.get_index_portfolio_deposit_file(index.ticker)
            if tickers:
                logger.info(f"{len(tickers)}개 종목 발견")
                return list(tickers)
        except Exception as e:
            logger.error(f"구성 종목 조회 실패: {e}")

        return []

    def collect_stock_data(self, tickers: List[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
        """개별 종목 데이터 수집"""
        logger.info(f"{len(tickers)}개 종목 데이터 수집 시작")

        # 날짜 인덱스 가져오기
        dates = stock.get_index_ohlcv(
            self.config.start_date,
            self.config.end_date,
            MarketIndex.KOSPI.ticker
        ).index

        # 데이터프레임 초기화
        close_data = pd.DataFrame(index=dates)
        volume_data = pd.DataFrame(index=dates)

        # 순차적으로 각 종목 데이터 수집
        for idx, ticker in enumerate(tickers, 1):
            try:
                # 진행상황 표시
                if idx % 10 == 0:
                    logger.info(f"진행중: {idx}/{len(tickers)}")

                # 종목 데이터 수집
                df = stock.get_market_ohlcv(
                    self.config.start_date,
                    self.config.end_date,
                    ticker
                )

                if df.empty:
                    continue

                # 종목명 가져오기
                ticker_name = stock.get_market_ticker_name(ticker)
                col_name = f"{ticker_name}({ticker})"

                # 날짜 인덱스에 맞춰 데이터 정렬
                df_reindexed = df.reindex(dates)
                close_data[col_name] = df_reindexed["종가"]
                volume_data[col_name] = df_reindexed["거래량"].fillna(0)

                time.sleep(self.config.api_delay)

            except Exception as e:
                logger.warning(f"{ticker} 수집 실패: {e}")
                continue

        # 날짜 컬럼 추가
        close_data.reset_index(names="날짜", inplace=True)
        volume_data.reset_index(names="날짜", inplace=True)

        logger.info(f"데이터 수집 완료: {len(close_data.columns)-1}개 종목")
        return close_data, volume_data


class MarketAnalyzer:
    """시장 분석"""

    def calculate_change_rate(self, prices: pd.Series) -> pd.Series:
        """변화율 계산"""
        return prices.pct_change().fillna(0)

    def analyze_market_data(
        self, close_df: pd.DataFrame, volume_df: pd.DataFrame
    ) -> Dict[str, pd.DataFrame]:
        """시장 데이터 분석"""
        logger.info("시장 데이터 분석 시작")

        # 주식 컬럼만 선택 (날짜 컬럼 제외)
        stock_cols = [col for col in close_df.columns if col != "날짜"]

        # 1. 변화율 계산
        logger.info("변화율 계산 중...")
        change_df = close_df.copy()
        for col in stock_cols:
            change_df[col] = self.calculate_change_rate(close_df[col])

        # 2. 상승/하락 거래량 분리
        logger.info("거래량 분리 중...")
        upside_df = volume_df.copy()
        downside_df = volume_df.copy()

        for col in stock_cols:
            # 상승한 종목의 거래량만
            upside_df[col] = volume_df[col].where(change_df[col] > 0, 0)
            # 하락한 종목의 거래량만
            downside_df[col] = volume_df[col].where(change_df[col] < 0, 0)

        # 3. 포인트 계산
        logger.info("포인트 계산 중...")
        gain_df = change_df.copy()
        lost_df = change_df.copy()

        for col in stock_cols:
            # 상승 포인트 (양수만)
            gain_df[col] = change_df[col].where(change_df[col] > 0, 0)
            # 하락 포인트 (음수만)
            lost_df[col] = change_df[col].where(change_df[col] < 0, 0)

        return {
            "change": change_df,
            "upside": upside_df,
            "downside": downside_df,
            "gain": gain_df,
            "lost": lost_df,
        }

    def create_summary_sheet(
        self,
        index_data: pd.DataFrame,
        analysis_results: Dict[str, pd.DataFrame],
        market_name: str,
    ) -> pd.DataFrame:
        """요약 시트 생성"""
        logger.info(f"{market_name} 요약 시트 생성")

        upside_df = analysis_results["upside"]
        downside_df = analysis_results["downside"]
        gain_df = analysis_results["gain"]
        lost_df = analysis_results["lost"]

        # 주식 컬럼만 선택
        stock_cols = [col for col in upside_df.columns if col != "날짜"]

        # 결과 데이터프레임 초기화
        result = pd.DataFrame()
        result["날짜"] = index_data["날짜"]
        result[market_name] = index_data["종가"]

        # 각 날짜별로 계산
        volume_list = []
        volume1_list = []
        overbought_oversold_list = []
        gained_list = []
        lost_list = []

        for i in range(len(upside_df)):
            # 해당 날짜의 값들 가져오기
            upside_vals = upside_df[stock_cols].iloc[i]
            downside_vals = downside_df[stock_cols].iloc[i]
            gain_vals = gain_df[stock_cols].iloc[i]
            lost_vals = lost_df[stock_cols].iloc[i]

            # 거래량 및 포인트 합산
            upside_sum = upside_vals.sum()
            downside_sum = downside_vals.sum()
            points_gained = gain_vals.sum()
            points_lost = lost_vals.sum()

            volume_list.append(upside_sum)
            volume1_list.append(downside_sum)
            gained_list.append(points_gained)
            lost_list.append(points_lost)

            # 과매수/과매도 계산
            total_vol = upside_sum + downside_sum
            total_points = points_gained + abs(points_lost)  # 절대값 사용

            if total_vol > 0 and total_points > 0:
                # 긍정적 지표 계산 (상승)
                positive_vol_percentage = upside_sum / total_vol
                positive_points_percentage = points_gained / total_points
                positive_average = (positive_vol_percentage + positive_points_percentage) / 2

                # 부정적 지표 계산 (하락)
                negative_vol_percentage = downside_sum / total_vol
                negative_points_percentage = abs(points_lost) / total_points  # 절대값 사용
                negative_average = (negative_vol_percentage + negative_points_percentage) / 2

                # 과매수/과매도: 상승이 우세하면 양수, 하락이 우세하면 음수
                if positive_average > negative_average:
                    overbought_oversold = positive_average
                else:
                    overbought_oversold = -negative_average
            else:
                overbought_oversold = np.nan

            overbought_oversold_list.append(overbought_oversold)

        # 계산된 값 할당
        result["Volume"] = volume_list
        result["Volume.1"] = volume1_list
        result["과매수/과매도"] = overbought_oversold_list
        result["gained"] = gained_list
        result["Lost"] = lost_list

        # 파생 지표 계산
        total_vol = result["Volume"] + result["Volume.1"]
        total_points = result["gained"] + result["Lost"].abs()  # 절대값 사용

        # 거래량 비율
        result["+VOL%"] = np.where(total_vol > 0, result["Volume"] / total_vol, 0)
        result["-VOL%"] = np.where(total_vol > 0, result["Volume.1"] / total_vol, 0)

        # 포인트 비율
        result["+POINTS%"] = np.where(total_points > 0, result["gained"] / total_points, 0)
        result["-POINTS%"] = np.where(total_points > 0, result["Lost"].abs() / total_points, 0)  # 절대값 사용

        # 평균 계산
        result["평균"] = (result["+VOL%"] + result["+POINTS%"]) / 2
        result["평균.1"] = (result["-VOL%"] + result["-POINTS%"]) / 2

        return result


class ExcelExporter:
    """엑셀 내보내기"""

    @staticmethod
    def export_market_data(filename: str, market_data: Dict[str, pd.DataFrame]) -> None:
        """엑셀 파일로 내보내기"""
        logger.info(f"{filename} 파일 생성 중...")

        try:
            with pd.ExcelWriter(filename, engine="openpyxl") as writer:
                for sheet_name, df in market_data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    logger.info(f"  - {sheet_name}: {len(df)}행")

            logger.info(f"파일 저장 완료: {filename}")

        except Exception as e:
            logger.error(f"엑셀 저장 실패: {e}")
            raise


class KoreaMarketDataPipeline:
    """메인 파이프라인"""

    def __init__(self, config: MarketConfig):
        self.config = config
        self.collector = StockDataCollector(config)
        self.analyzer = MarketAnalyzer()
        self.exporter = ExcelExporter()

    def process_market(
        self,
        index: MarketIndex,
        component_index: MarketIndex,
        index_data: Dict[str, pd.DataFrame],
    ) -> Dict[str, pd.DataFrame]:
        """개별 시장 처리"""
        logger.info(f"\n{'='*60}")
        logger.info(f"{index.display_name} 시장 처리 시작")
        logger.info(f"{'='*60}")

        # 1. 구성 종목 조회
        components = self.collector.get_index_components(component_index)
        if not components:
            logger.error(f"{component_index.display_name} 구성 종목을 찾을 수 없습니다")
            return {}

        # 2. 종목 데이터 수집
        close_df, volume_df = self.collector.collect_stock_data(components)

        # 3. 데이터 분석
        analysis_results = self.analyzer.analyze_market_data(close_df, volume_df)

        # 4. 요약 시트 생성
        summary = self.analyzer.create_summary_sheet(
            index_data[index.display_name],
            analysis_results,
            index.display_name
        )

        # 5. 내보낼 데이터 구성
        market_data = {
            f"{index.korean_name}최종": summary,
            f"{component_index.korean_name}종목": pd.DataFrame({"종목코드": components}),
            index.display_name: index_data[index.display_name],
            "거래량": volume_df,
            "종가": close_df,
            "변화율": analysis_results["change"],
            "UPSIDE 거래량": analysis_results["upside"],
            "DOWNSIDE 거래량": analysis_results["downside"],
            "Point gain": analysis_results["gain"],
            "Point lost": analysis_results["lost"],
        }

        return market_data

    def run(self) -> None:
        """전체 파이프라인 실행"""
        start_time = time.time()

        logger.info("\n" + "="*60)
        logger.info("한국 주식 시장 데이터 수집 및 분석")
        logger.info(f"기간: {self.config.start_date} ~ {self.config.end_date}")
        logger.info("="*60 + "\n")

        try:
            # 1. 지수 데이터 수집
            index_data = self.collector.collect_index_data(
                [MarketIndex.KOSPI, MarketIndex.KOSDAQ]
            )

            if not index_data:
                logger.error("지수 데이터 수집 실패")
                return

            # 2. KOSPI 처리
            kospi_data = self.process_market(
                MarketIndex.KOSPI,
                MarketIndex.KOSPI200,
                index_data
            )

            # 3. KOSDAQ 처리
            kosdaq_data = self.process_market(
                MarketIndex.KOSDAQ,
                MarketIndex.KOSDAQ150,
                index_data
            )

            # 4. 엑셀 파일 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if kospi_data:
                filename = f"코스피_SIO_{timestamp}.xlsx"
                self.exporter.export_market_data(filename, kospi_data)
                self._print_summary("KOSPI", kospi_data["코스피최종"])

            if kosdaq_data:
                filename = f"코스닥_SIO_{timestamp}.xlsx"
                self.exporter.export_market_data(filename, kosdaq_data)
                self._print_summary("KOSDAQ", kosdaq_data["코스닥최종"])

            # 완료
            elapsed_time = time.time() - start_time
            logger.info("\n" + "="*60)
            logger.info(f"전체 처리 완료: {elapsed_time:.2f}초 소요")
            logger.info("="*60)

        except Exception as e:
            logger.error(f"파이프라인 실행 실패: {e}")
            raise

    def _print_summary(self, market: str, summary_df: pd.DataFrame) -> None:
        """시장 요약 출력"""
        logger.info(f"\n{market} 요약 (최근 5일):")
        print(summary_df[["날짜", market, "과매수/과매도"]].tail())


def main():
    """메인 함수"""
    try:
        # 설정
        config = MarketConfig(
            start_date="20240401",
            end_date="20240603",
            api_delay=0.1,
        )

        # 파이프라인 실행
        pipeline = KoreaMarketDataPipeline(config)
        pipeline.run()

    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"치명적 오류: {e}")
        raise


if __name__ == "__main__":
    main()
