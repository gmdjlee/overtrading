"""
시장 분석 테스트 코드
2024년 4월 1일 ~ 2024년 6월 3일 기간 동안
지정된 코스피 종목으로 데이터 검증
"""

import logging
import time
from datetime import datetime
from typing import Dict, List

import pandas as pd
from pykrx import stock

from market_analysis_simple import (
    MarketConfig,
    MarketAnalyzer,
    MarketIndex,
    StockDataCollector,
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# 테스트용 코스피200 종목 (2024년 4월 1일 ~ 2024년 6월 3일 기준)
TEST_KOSPI200_STOCKS = [
    "하이트진로", "유한양행", "CJ대한통운", "두산", "DL", "한국앤컴퍼니", "기아", "SK하이닉스",
    "영풍", "현대건설", "삼성화재", "한화", "DB하이텍", "CJ", "LX인터내셔널", "세아베스틸지주",
    "대한전선", "현대해상", "금양", "대상", "SK네트웍스", "오리온홀딩스", "KCC", "TCC스틸",
    "아모레G", "대웅", "삼양식품", "쌍용C&E", "대한항공", "LG", "KG모빌리티", "포스코퓨처엠",
    "롯데정밀화학", "현대제철", "신세계", "농심", "세방전지", "효성", "롯데지주", "녹십자홀딩스",
    "롯데칠성", "현대차", "코스모화학", "POSCO홀딩스", "DB손해보험", "에스엘", "삼성전자", "NH투자증권",
    "삼아알미늄", "LS", "녹십자", "GS건설", "삼성SDI", "대한유화", "미래에셋증권", "GS리테일",
    "오뚜기", "율촌화학", "호텔신라", "한미사이언스", "삼성전기", "한샘", "한올바이오파마", "HD한국조선해양",
    "한화솔루션", "명신산업", "영원무역홀딩스", "OCI홀딩스", "LS ELECTRIC", "고려아연", "삼성중공업", "HD현대미포",
    "아이에스동서", "S-Oil", "LG이노텍", "롯데케미칼", "HMM", "현대위아", "금호석유", "SKC",
    "현대모비스", "한화에어로스페이스", "에스원", "한솔케미칼", "동원시스템즈", "한국전력", "삼성증권", "KG스틸",
    "SK텔레콤", "현대엘리베이", "삼성에스디에스", "한온시스템", "신풍제약", "롯데에너지머티리얼즈", "아시아나항공", "코웨이",
    "포스코DX", "롯데쇼핑", "기업은행", "동서", "삼성E&A", "삼성물산", "팬오션", "삼성카드",
    "제일기획", "KT", "롯데관광개발", "LG유플러스", "삼성생명", "KT&G", "두산에너빌리티", "LG디스플레이",
    "SK", "강원랜드", "NAVER", "카카오", "한국가스공사", "엔씨소프트", "하나투어", "키움증권",
    "한화오션", "HD현대인프라코어", "대우건설", "포스코인터내셔널", "한국항공우주", "한전KPS", "LG생활건강", "LG화학",
    "한전기술", "신한지주", "현대로템", "LG전자", "셀트리온", "TKG휴켐스", "대웅제약", "현대백화점",
    "한국금융지주", "금호타이어", "GS", "LIG넥스원", "휠라홀딩스", "현대글로비스", "하나금융지주", "한화생명",
    "아모레퍼시픽", "후성", "SK이노베이션", "CJ제일제당", "풍산", "KB금융", "한세실업", "영원무역",
    "씨에스윈드", "GKL", "코오롱인더", "한미약품", "에스디바이오센서", "메리츠금융지주", "BNK금융지주", "DGB금융지주",
    "이마트", "덴티움", "한국타이어앤테크놀로지", "한국콜마", "JB금융지주", "PI첨단소재", "한진칼", "종근당",
    "더블유게임즈", "코스맥스", "HL만도", "삼성바이오로직스", "두산밥캣", "넷마블", "크래프톤", "HD현대",
    "HD현대일렉트릭", "오리온", "일진하이솔루스", "한화시스템", "롯데웰푸드", "BGF리테일", "SK케미칼", "효성티앤씨",
    "효성첨단소재", "한일시멘트", "SK바이오사이언스", "우리금융지주", "카카오뱅크", "SK바이오팜", "HD현대중공업", "두산퓨얼셀",
    "하이브", "SK아이이테크놀로지", "LG에너지솔루션", "DL이앤씨", "카카오페이", "F&F", "SK스퀘어", "에코프로머티"
]


class TestMarketDataCollector:
    """테스트용 데이터 수집기"""

    def __init__(self, config: MarketConfig):
        self.config = config
        self.collector = StockDataCollector(config)
        self.analyzer = MarketAnalyzer()

    def get_ticker_from_name(self, stock_name: str, date: str) -> str:
        """종목명으로 종목코드 찾기"""
        try:
            # KOSPI 전체 종목 조회
            tickers = stock.get_market_ticker_list(date, market="KOSPI")

            for ticker in tickers:
                name = stock.get_market_ticker_name(ticker)
                if name == stock_name:
                    return ticker

            logger.warning(f"종목 '{stock_name}'의 티커를 찾을 수 없습니다")
            return None

        except Exception as e:
            logger.error(f"종목 '{stock_name}' 티커 조회 실패: {e}")
            return None

    def get_test_tickers(self) -> List[str]:
        """테스트용 종목 코드 목록 가져오기"""
        logger.info("테스트용 종목 코드 수집 시작")
        tickers = []

        for stock_name in TEST_KOSPI200_STOCKS:
            ticker = self.get_ticker_from_name(stock_name, self.config.end_date)
            if ticker:
                tickers.append(ticker)
                logger.info(f"  {stock_name}: {ticker}")
            else:
                logger.warning(f"  {stock_name}: 티커를 찾을 수 없음")

            time.sleep(0.05)  # API 부하 방지

        logger.info(f"\n총 {len(tickers)}/{len(TEST_KOSPI200_STOCKS)}개 종목 코드 수집 완료")
        return tickers

    def run_test(self) -> Dict[str, pd.DataFrame]:
        """테스트 실행"""
        logger.info("\n" + "="*60)
        logger.info("시장 분석 테스트 시작")
        logger.info(f"기간: {self.config.start_date} ~ {self.config.end_date}")
        logger.info(f"테스트 종목 수: {len(TEST_KOSPI200_STOCKS)}개")
        logger.info("="*60 + "\n")

        start_time = time.time()

        try:
            # 1. 지수 데이터 수집
            logger.info("1. KOSPI 지수 데이터 수집")
            index_data = self.collector.collect_index_data([MarketIndex.KOSPI])

            if not index_data:
                logger.error("지수 데이터 수집 실패")
                return None

            # 2. 테스트 종목 티커 가져오기
            logger.info("\n2. 테스트 종목 티커 수집")
            tickers = self.get_test_tickers()

            if len(tickers) == 0:
                logger.error("종목 티커를 찾을 수 없습니다")
                return None

            # 3. 종목 데이터 수집
            logger.info(f"\n3. {len(tickers)}개 종목 데이터 수집")
            close_df, volume_df = self.collector.collect_stock_data(tickers)

            # 4. 데이터 분석
            logger.info("\n4. 시장 데이터 분석")
            analysis_results = self.analyzer.analyze_market_data(close_df, volume_df)

            # 5. 요약 시트 생성
            logger.info("\n5. 요약 시트 생성")
            summary = self.analyzer.create_summary_sheet(
                index_data["KOSPI"],
                analysis_results,
                "KOSPI"
            )

            # 6. 결과 검증
            logger.info("\n6. 결과 검증")
            self.validate_results(summary, close_df, volume_df, analysis_results)

            # 7. 결과 반환
            elapsed_time = time.time() - start_time
            logger.info("\n" + "="*60)
            logger.info(f"테스트 완료: {elapsed_time:.2f}초 소요")
            logger.info("="*60)

            return {
                "summary": summary,
                "close": close_df,
                "volume": volume_df,
                "analysis": analysis_results,
                "tickers": pd.DataFrame({
                    "종목코드": tickers,
                    "종목명": [stock.get_market_ticker_name(t) for t in tickers]
                })
            }

        except Exception as e:
            logger.error(f"테스트 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

    def validate_results(
        self,
        summary: pd.DataFrame,
        close_df: pd.DataFrame,
        volume_df: pd.DataFrame,
        analysis_results: Dict[str, pd.DataFrame]
    ):
        """결과 검증"""
        logger.info("\n=== 결과 검증 ===")

        # 1. 데이터 건수 확인
        logger.info(f"\n1. 데이터 건수:")
        logger.info(f"  - 요약 데이터: {len(summary)}행")
        logger.info(f"  - 종가 데이터: {len(close_df)}행 x {len(close_df.columns)-1}개 종목")
        logger.info(f"  - 거래량 데이터: {len(volume_df)}행 x {len(volume_df.columns)-1}개 종목")

        # 2. 요약 데이터 샘플 출력
        logger.info(f"\n2. 요약 데이터 (최근 5일):")
        print(summary[["날짜", "KOSPI", "과매수/과매도", "+VOL%", "-VOL%", "평균", "평균.1"]].tail())

        # 3. 과매수/과매도 값 범위 확인
        logger.info(f"\n3. 과매수/과매도 통계:")
        overbought_oversold = summary["과매수/과매도"].dropna()
        if len(overbought_oversold) > 0:
            logger.info(f"  - 최소값: {overbought_oversold.min():.4f}")
            logger.info(f"  - 최대값: {overbought_oversold.max():.4f}")
            logger.info(f"  - 평균값: {overbought_oversold.mean():.4f}")
            logger.info(f"  - NaN 개수: {summary['과매수/과매도'].isna().sum()}개")

        # 4. 비율 합계 검증 (각 날짜별로 +VOL% + -VOL% = 1, +POINTS% + -POINTS% = 1)
        logger.info(f"\n4. 비율 합계 검증:")
        vol_sum = (summary["+VOL%"] + summary["-VOL%"]).round(6)
        points_sum = (summary["+POINTS%"] + summary["-POINTS%"]).round(6)

        vol_check = (vol_sum == 1.0).all() or ((vol_sum - 1.0).abs() < 0.0001).all()
        points_check = (points_sum == 1.0).all() or ((points_sum - 1.0).abs() < 0.0001).all()

        logger.info(f"  - 거래량 비율 합계 = 1: {'✓ 통과' if vol_check else '✗ 실패'}")
        logger.info(f"  - 포인트 비율 합계 = 1: {'✓ 통과' if points_check else '✗ 실패'}")

        # 5. 평균 계산 검증
        logger.info(f"\n5. 평균 계산 검증:")
        calculated_avg = ((summary["+VOL%"] + summary["+POINTS%"]) / 2).round(6)
        calculated_avg1 = ((summary["-VOL%"] + summary["-POINTS%"]) / 2).round(6)

        avg_check = (summary["평균"].round(6) == calculated_avg).all()
        avg1_check = (summary["평균.1"].round(6) == calculated_avg1).all()

        logger.info(f"  - 평균 = (상승거래량% + 상승포인트%) / 2: {'✓ 통과' if avg_check else '✗ 실패'}")
        logger.info(f"  - 평균.1 = (하락거래량% + 하락포인트%) / 2: {'✓ 통과' if avg1_check else '✗ 실패'}")

        # 6. 과매수/과매도 계산 검증
        logger.info(f"\n6. 과매수/과매도 계산 검증:")

        # 샘플 날짜로 검증 (마지막 날)
        last_idx = len(summary) - 1
        last_row = summary.iloc[last_idx]

        expected_overbought_oversold = max(last_row["평균"], last_row["평균.1"])
        actual_overbought_oversold = last_row["과매수/과매도"]

        logger.info(f"  - 마지막 날짜: {last_row['날짜']}")
        logger.info(f"  - 평균: {last_row['평균']:.6f}")
        logger.info(f"  - 평균.1: {last_row['평균.1']:.6f}")
        logger.info(f"  - 예상 과매수/과매도: {expected_overbought_oversold:.6f}")
        logger.info(f"  - 실제 과매수/과매도: {actual_overbought_oversold:.6f}")

        if abs(expected_overbought_oversold - actual_overbought_oversold) < 0.0001:
            logger.info(f"  - 과매수/과매도 = max(평균, 평균.1): ✓ 통과")
        else:
            logger.warning(f"  - 과매수/과매도 = max(평균, 평균.1): ✗ 실패")

        logger.info("\n=== 검증 완료 ===\n")


def export_test_results(test_data: Dict[str, pd.DataFrame], filename: str = None):
    """테스트 결과를 엑셀 파일로 저장"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"테스트_코스피_SIO_{timestamp}.xlsx"

    logger.info(f"테스트 결과를 {filename}에 저장 중...")

    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        # 요약 시트
        test_data["summary"].to_excel(writer, sheet_name="코스피최종", index=False)

        # 종목 목록
        test_data["tickers"].to_excel(writer, sheet_name="테스트종목", index=False)

        # 원본 데이터
        test_data["close"].to_excel(writer, sheet_name="종가", index=False)
        test_data["volume"].to_excel(writer, sheet_name="거래량", index=False)

        # 분석 결과
        test_data["analysis"]["change"].to_excel(writer, sheet_name="변화율", index=False)
        test_data["analysis"]["upside"].to_excel(writer, sheet_name="UPSIDE 거래량", index=False)
        test_data["analysis"]["downside"].to_excel(writer, sheet_name="DOWNSIDE 거래량", index=False)
        test_data["analysis"]["gain"].to_excel(writer, sheet_name="Point gain", index=False)
        test_data["analysis"]["lost"].to_excel(writer, sheet_name="Point lost", index=False)

    logger.info(f"저장 완료: {filename}")


def main():
    """메인 함수"""
    try:
        # 테스트 설정
        config = MarketConfig(
            start_date="20240401",
            end_date="20240603",
            api_delay=0.1,
        )

        # 테스트 실행
        tester = TestMarketDataCollector(config)
        test_data = tester.run_test()

        if test_data:
            # 결과 저장
            export_test_results(test_data)

            logger.info("\n테스트가 성공적으로 완료되었습니다!")
        else:
            logger.error("\n테스트가 실패했습니다.")

    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"\n치명적 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
