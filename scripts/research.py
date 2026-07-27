"""
Research Module - 키워드/제품 정보 수집 및 분석
"""
import json
import yaml
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict

@dataclass
class ProductInfo:
    name: str
    category: str
    price: str
    specs: dict
    pros: list
    cons: list
    source_urls: list
    release_date: str = ""

@dataclass
class ResearchResult:
    keyword: str
    products: list
    related_keywords: list
    search_intent: str
    created_at: str

def load_config():
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class ResearchModule:
    """키워드 리서치 및 제품 정보 수집"""
    
    def __init__(self):
        self.config = load_config()
    
    def research(self, keyword: str) -> ResearchResult:
        """
        키워드를 입력받아 관련 제품 정보를 수집합니다.
        
        Args:
            keyword: 검색 키워드 (예: "가성비 노트북 추천")
            
        Returns:
            ResearchResult: 수집된 정보
        """
        print(f"🔍 리서치 시작: '{keyword}'")
        
        # 1. 키워드 분석 (관련 검색어, 검색 의도 추론)
        related = self._analyze_keyword(keyword)
        
        # 2. LLM을 통해 제품 스펙/정보 수집 (실제로는 웹 검색 + LLM)
        products = self._gather_products(keyword, related)
        
        # 3. 결과 저장
        result = ResearchResult(
            keyword=keyword,
            products=products,
            related_keywords=related,
            search_intent=self._infer_intent(keyword),
            created_at=datetime.now().isoformat()
        )
        
        self._save_research(result)
        print(f"✅ 리서치 완료: {len(products)}개 제품 발견")
        return result
    
    def _analyze_keyword(self, keyword: str) -> list:
        """키워드 분석 - 관련 검색어 생성"""
        # LLM 호출로 관련 키워드 생성 (실제 구현시 API 호출)
        # 여기서는 구조만 보여줌
        related = [
            f"{keyword} 2025",
            f"{keyword} 가격",
            f"{keyword} 순위",
            f"{keyword} 장단점",
        ]
        return related
    
    def _gather_products(self, keyword: str, related: list) -> list:
        """제품 정보 수집 (스펙, 가격, 장단점)"""
        # 실제로는 LLM + 웹 검색 조합
        # 여기서는 AI가 생성한 제품 정보를 받아옴
        products = []
        return products
    
    def _infer_intent(self, keyword: str) -> str:
        """검색 의도 분석"""
        # '비교', '추천' → 구매 의도
        # '종류', '차이' → 정보 탐색
        # '가격', '할인' → 가격 비교
        buy_keywords = ['추천', '비교', 'top', '순위', '가성비', '괜찮은']
        info_keywords = ['종류', '차이', '뜻', '원리', '방법']
        price_keywords = ['가격', '할인', '싼', '저렴한', '가성비']
        
        for kw in buy_keywords:
            if kw in keyword:
                return "구매 의도 (구매 전환 가능성 높음)"
        for kw in price_keywords:
            if kw in keyword:
                return "가격 비교 의도"
        return "정보 탐색 의도"
    
    def _save_research(self, result: ResearchResult):
        """리서치 결과 저장"""
        output_dir = Path(__file__).parent / "content" / "drafts"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)
        print(f"  📄 리서치 저장: {filepath}")


if __name__ == "__main__":
    # 테스트
    rm = ResearchModule()
    rm.research("가성비 노트북 추천")
