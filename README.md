# 한국 주식 시장 분석 도구

## 파일 설명

### market_analysis_simple.py
병렬처리, 캐시 등의 최적화 기능을 제거하고 핵심 기능만 남긴 단순화된 버전입니다.

## 주요 변경사항

### 제거된 기능
1. **DataCache 클래스** - 메모리 캐싱 기능 제거
2. **병렬 처리** - ThreadPoolExecutor를 사용한 멀티스레딩 제거
3. **배치 처리** - batch_size, max_workers, chunk_size 등 최적화 파라미터 제거
4. **청크 단위 처리** - 대용량 데이터를 나눠서 처리하는 로직 제거

### 단순화된 구조

#### 1. MarketConfig
```python
# 이전: 최적화 파라미터 포함
MarketConfig(start_date, end_date, api_delay, batch_size, max_workers, chunk_size)

# 단순화: 필수 파라미터만
MarketConfig(start_date, end_date, api_delay)
```

#### 2. 데이터 수집
```python
# 이전: 병렬 처리
collect_stock_data_parallel() → ThreadPoolExecutor로 동시 처리

# 단순화: 순차 처리
collect_stock_data() → 간단한 for 루프로 순차 처리
```

#### 3. 캐싱
```python
# 이전: 캐시 확인 후 API 호출
cached = self.cache.get(cache_key)
if cached is not None:
    return cached

# 단순화: 직접 API 호출
df = stock.get_index_ohlcv(...)
```

## 주요 클래스

### StockDataCollector
- `collect_index_data()`: 지수 데이터 수집 (KOSPI, KOSDAQ)
- `get_index_components()`: 지수 구성 종목 조회
- `collect_stock_data()`: 개별 종목 데이터 수집 (순차 처리)

### MarketAnalyzer
- `calculate_change_rate()`: 변화율 계산
- `analyze_market_data()`: 시장 데이터 분석
  - 변화율 계산
  - 상승/하락 거래량 분리
  - 포인트 계산
- `create_summary_sheet()`: 요약 시트 생성
  - 과매수/과매도 지표
  - 거래량 및 포인트 비율

### ExcelExporter
- `export_market_data()`: 엑셀 파일로 결과 저장

## 사용 방법

```python
from market_analysis_simple import MarketConfig, KoreaMarketDataPipeline

# 설정
config = MarketConfig(
    start_date="20240401",
    end_date="20240603",
    api_delay=0.1,  # API 호출 간 대기 시간 (초)
)

# 실행
pipeline = KoreaMarketDataPipeline(config)
pipeline.run()
```

## 출력 파일

- `코스피_SIO_YYYYMMDD_HHMMSS.xlsx`
- `코스닥_SIO_YYYYMMDD_HHMMSS.xlsx`

각 파일에는 다음 시트가 포함됩니다:
- 코스피최종/코스닥최종: 요약 데이터
- 코스피200종목/코스닥150종목: 구성 종목 목록
- KOSPI/KOSDAQ: 지수 데이터
- 거래량: 전체 거래량
- 종가: 종가 데이터
- 변화율: 일별 변화율
- UPSIDE 거래량: 상승 종목 거래량
- DOWNSIDE 거래량: 하락 종목 거래량
- Point gain: 상승 포인트
- Point lost: 하락 포인트

## 장점

1. **이해하기 쉬운 코드**: 순차적 처리로 로직 흐름 파악 용이
2. **단순한 구조**: 복잡한 최적화 로직 없이 핵심 기능만 포함
3. **유지보수 용이**: 디버깅과 수정이 간단함
4. **낮은 메모리 사용**: 캐싱 없이 필요한 만큼만 메모리 사용

## 단점

1. **느린 실행 속도**: 병렬 처리가 없어 처리 시간이 길어짐
2. **반복 API 호출**: 캐시가 없어 같은 데이터를 여러 번 호출할 수 있음
3. **대용량 데이터 처리 제한**: 청크 처리가 없어 매우 큰 데이터셋에는 부적합

## 의존성

```bash
pip install pykrx pandas numpy openpyxl
```
