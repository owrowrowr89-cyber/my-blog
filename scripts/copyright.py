"""
Copyright Module - 저작권/표절 검증 및 오리지널리티 체크

AI가 생성한 콘텐츠의 독창성을 검증하고, 기존 콘텐츠와의
유사도를 분석하여 저작권 리스크를 최소화합니다.
"""
import re
import yaml
import hashlib
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class CopyrightVerdict:
    """저작권 검증 결과"""
    is_safe: bool                    # 안전한 콘텐츠인가?
    originality_score: int           # 독창성 점수 (0-100)
    similarity_ratio: float          # 유사도 비율
    flagged_phrases: List[str]       # 문제 의심 구문
    suggestions: List[str]           # 개선 제안
    risk_level: str                  # safe / caution / dangerous


class CopyrightVerifier:
    """
    AI 생성 콘텐츠의 저작권 리스크를 검증합니다.
    
    검증 항목:
    1. 표절/의역 패턴 감지
    2. 뻔한 AI 표현 필터링
    3. 상표/브랜드명 적절성 확인
    4. 사실 정보 왜곡 체크
    5. 오리지널리티 점수 산출
    """
    
    # AI 생성문에서 자주 나오는 뻔한 표현 패턴
    AI_CLICHE_PATTERNS = [
        r"당신의\s.*(?:선택|여정|생활|경험)",
        r"완벽한\s.*(?:선택|조화|솔루션)",
        r"더\s이상\s.*(?:고민|걱정|망설)",
        r"혁신적인\s.*(?:기술|제품|디자인)",
        r"한계를\s넘어",
        r"새로운\s.*(?:기준|패러다임|차원)",
        r"과감한\s.*(?:선택|도전|시도)",
        r"놀라운\s.*(?:경험|성능|결과)",
        r"차원이\s다른",
        r"최고의\s.*(?:성능|선택|경험)",
    ]
    
    # 의심스러운 문장 패턴 (원본과 유사할 가능성)
    SUSPICIOUS_PATTERNS = [
        r"라고\s(?:합니다|해요|하죠|해볼까요)",
        r"한번\s.*(?:확인|살펴|알아)",
        r"참고하시면\s좋습니다",
        r"도움이\s되셨으면\s좋겠습니다",
        r"마지막으로\s추천",
    ]
    
    def __init__(self):
        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
    
    def verify(self, content: str, title: str = "") -> CopyrightVerdict:
        """
        전체 콘텐츠 저작권 검증
        
        Args:
            content: 검증할 콘텐츠 (마크다운)
            title: 글 제목
            
        Returns:
            CopyrightVerdict: 검증 결과
        """
        flagged = []
        suggestions = []
        
        # 1. AI 뻔한 표현 체크
        cliches_found = self._check_ai_cliches(content)
        if cliches_found:
            flagged.append(f"AI 전형적인 표현 {len(cliches_found)}개 발견")
            suggestions.append(f"'{cliches_found[0]}' 같은 표현을 더 자연스럽게 바꿔보세요")
        
        # 2. 길이/다양성 검사
        diversity_score = self._check_vocabulary_diversity(content)
        if diversity_score < 0.4:
            flagged.append("어휘 다양성이 낮습니다 (같은 단어 반복)")
            suggestions.append("다양한 표현으로 문장을 바꿔보세요")
        
        # 3. 문장 구조 다양성
        structure_score = self._check_sentence_structure(content)
        if structure_score < 0.5:
            flagged.append("문장 구조가 단조롭습니다")
            suggestions.append("짧은 문장과 긴 문장을 섞어서 리듬감을 주세요")
        
        # 4. 출처/인용 표시 확인
        has_sources = self._check_source_citations(content)
        if not has_sources:
            suggestions.append("특정 가격/스펙 정보는 출처를 표시하는 것이 좋습니다")
        
        # 5. 저작권 위험 표현 체크
        risk_phrases = self._check_risk_phrases(content)
        if risk_phrases:
            flagged.extend(risk_phrases)
        
        # 6. 상표명 과다 사용 체크
        brand_density = self._check_brand_density(content)
        if brand_density > 0.15:
            suggestions.append("특정 브랜드명 반복 사용을 줄이고 '이 제품' 등으로 대체하세요")
        
        # 점수 산출
        originality_score = self._calculate_originality_score(
            len(flagged), cliches_found, diversity_score
        )
        
        similarity_ratio = 1.0 - (originality_score / 100)
        
        # 위험도 판정
        risk_level = self._determine_risk_level(originality_score, len(flagged))
        
        return CopyrightVerdict(
            is_safe=risk_level == "safe",
            originality_score=originality_score,
            similarity_ratio=similarity_ratio,
            flagged_phrases=flagged,
            suggestions=suggestions,
            risk_level=risk_level
        )
    
    def _check_ai_cliches(self, text: str) -> List[str]:
        """AI 뻔한 표현 패턴 찾기"""
        found = []
        for pattern in self.AI_CLICHE_PATTERNS:
            matches = re.findall(pattern, text)
            found.extend(matches)
        return found[:10]  # 최대 10개
    
    def _check_vocabulary_diversity(self, text: str) -> float:
        """
        어휘 다양성 체크 (Type-Token Ratio)
        1에 가까울수록 다양한 어휘 사용
        """
        words = re.findall(r'[가-힣a-zA-Z]+', text)
        if not words:
            return 1.0
        unique_words = len(set(words))
        total_words = len(words)
        return unique_words / total_words if total_words > 0 else 1.0
    
    def _check_sentence_structure(self, text: str) -> float:
        """문장 구조 다양성 체크"""
        sentences = re.split(r'[.!?]\s+', text)
        if len(sentences) < 3:
            return 1.0
        
        lengths = [len(s) for s in sentences if len(s) > 5]
        if not lengths:
            return 0.5
        
        avg = sum(lengths) / len(lengths)
        variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
        
        # 분산이 클수록 다양한 길이의 문장 → 자연스러움
        normalized = min(variance / 500, 1.0)
        return normalized
    
    def _check_source_citations(self, text: str) -> bool:
        """
        출처/인용 표시를 했는지 확인
        가격/수치 정보에 출처가 있는지 체크
        """
        source_patterns = [
            r"출처\s*:",
            r"기준\s*:",
            r"\([^)]*202[4-6][^)]*\)",  # 연도 표시
            r"참고\s*:",
        ]
        for pattern in source_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _check_risk_phrases(self, text: str) -> List[str]:
        """
        저작권 위험 표현 체크
        - 특정 블로그/사이트의 전형적인 표현
        - 의심스러운 일반론
        """
        risks = []
        
        # 절대적 표현 (과장광고 위험)
        absolutes = re.findall(r"(?:최고|완벽|최강|절대|영원히|모든).{0,10}(?:입니다|에요|하죠)", text)
        if absolutes:
            risks.append(f"과장 표현 {len(absolutes)}개: '{absolutes[0]}' - 광고 규제 위험 가능성")
        
        # 타사의 부정적 표현 (명예훼손 위험)
        negatives = re.findall(r"(?:쓰레기|형편없|최악|별로|실패)", text)
        if negatives:
            risks.append("부정적 표현 감지: 객관적 사실인지 확인 필요")
        
        return risks
    
    def _check_brand_density(self, text: str) -> float:
        """특정 브랜드명 반복 밀도 체크"""
        brands = re.findall(r'(?:삼성|LG|애플|Apple|Samsung|갤럭시|아이폰|맥북|레노버|ASUS|HP|DELL)', text)
        words = re.findall(r'[가-힣a-zA-Z]+', text)
        if not words:
            return 0
        return len(brands) / len(words)
    
    def _calculate_originality_score(self, 
                                     flagged_count: int, 
                                     cliches: List[str],
                                     diversity: float) -> int:
        """
        독창성 점수 계산 (0-100)
        
        감점 요소:
        - 문제 구문 1개당 -10점
        - AI 클리셰 1개당 -5점
        - 부족한 다양성 -20점
        """
        score = 100
        
        score -= flagged_count * 10
        score -= len(cliches) * 5
        
        if diversity < 0.3:
            score -= 20
        elif diversity < 0.4:
            score -= 10
        
        return max(0, min(100, score))
    
    def _determine_risk_level(self, score: int, flags: int) -> str:
        """위험도 판정"""
        if score >= 70 and flags <= 1:
            return "safe"
        elif score >= 40:
            return "caution"
        else:
            return "dangerous"
    
    def generate_improvement_prompt(self, content: str, verdict: CopyrightVerdict) -> str:
        """
        저작권/품질 개선을 위한 LLM 프롬프트 생성
        """
        prompt = f"""다음 블로그 글을 더 자연스럽고 독창적으로 개선해주세요.

## 현재 문제점
{' '.join(verdict.flagged_phrases)}

## 개선 방향
- {' '.join(verdict.suggestions)}

## 원본 글
{content[:2000]}

## 요구사항
1. AI 뻔한 표현 제거 (예: '당신의 선택', '혁신적인 기술' 등)
2. 더 다양한 어휘와 문장 구조 사용
3. 필요시 개인 경험/의견을 자연스럽게 추가
4. 기존 정보(스펙, 가격)는 그대로 유지
5. 전체 분량은 원본과 비슷하게 유지
"""
        return prompt


if __name__ == "__main__":
    # 테스트
    verifier = CopyrightVerifier()
    test_content = """
    당신의 완벽한 선택이 될 노트북을 소개합니다. 
    혁신적인 기술이 적용된 맥북 에어 M4는 
    당신의 생활을 완전히 바꿔놓을 것입니다.
    놀라운 성능과 차원이 다른 경험을 제공합니다.
    최고의 선택, 바로 맥북 에어입니다!
    """
    result = verifier.verify(test_content)
    print(f"안전: {result.is_safe}")
    print(f"독창성 점수: {result.originality_score}/100")
    print(f"위험도: {result.risk_level}")
    print(f"지적사항: {result.flagged_phrases}")
    print(f"개선제안: {result.suggestions}")
