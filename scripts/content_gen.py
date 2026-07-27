"""
Content Generator Module - AI 기반 다단계 블로그 콘텐츠 생성

5단계 생성 프로세스:
1. 제목/개요 생성
2. 제품 스펙 수집 + 비교표 생성  
3. 본문 생성 (도입부 → 본론 → 결론)
4. SEO 메타 정보 생성
5. 최종 품질 검수
"""
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import json, yaml, os, re
from pathlib import Path

from research import ResearchModule, ResearchResult
from marketing import MarketingEngine, MarketingElements
from copyright import CopyrightVerifier, CopyrightVerdict

@dataclass
class GeneratedPost:
    title: str
    description: str
    slug: str
    tags: list
    content: str            # Full markdown content
    hero_image: str         # Relative image path
    pub_date: str           # ISO date
    status: str             # draft / approved / published / rejected
    review_notes: str       # 검수 코멘트

class ContentPipeline:
    """
    5단계 콘텐츠 생성 파이프라인
    
    Flow:
    Input → 1차 생성 → 확장 → SEO → 저작권검증 → 마케팅강화 → 검수 → 발행
    """
    
    def __init__(self):
        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        
        self.research = ResearchModule()
        self.marketing = MarketingEngine()
        self.copyright_v = CopyrightVerifier()
        
        # 컨텐츠 저장소
        self.drafts_dir = Path(__file__).parent / "content" / "drafts"
        self.published_dir = Path(__file__).parent / "content" / "published"
        self.rejected_dir = Path(__file__).parent / "content" / "rejected"
        
        for d in [self.drafts_dir, self.published_dir, self.rejected_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def generate(self, keyword: str) -> GeneratedPost:
        """
        키워드 → 완성된 블로그 포스트 생성
        
        Args:
            keyword: 생성할 콘텐츠의 키워드/주제
            
        Returns:
            GeneratedPost: 생성된 포스트 (draft 상태)
        """
        print(f"\n{'='*50}")
        print(f"📝 콘텐츠 생성 시작: '{keyword}'")
        print(f"{'='*50}")
        
        # Step 1: 리서치
        print("\n[1/5] 🔍 리서치 중...")
        research = self.research.research(keyword)
        
        # Step 2: LLM 초안 생성 (실제로는 DeepSeek API 호출)
        print("\n[2/5] ✍️ AI 초안 생성 중...")
        draft = self._create_draft(keyword, research)
        
        # Step 3: 저작권 검증
        print(f"\n[3/5] 🔎 저작권 검증 중...")
        copyright_result = self.copyright_v.verify(draft["content"], draft["title"])
        print(f"  → 독창성 점수: {copyright_result.originality_score}/100")
        print(f"  → 위험도: {copyright_result.risk_level}")
        
        if copyright_result.risk_level == "dangerous":
            print("  ⚠️ 위험도 높음! 개선 프롬프트 생성...")
            improvement_prompt = self.copyright_v.generate_improvement_prompt(
                draft["content"], copyright_result
            )
            draft["copyright_notes"] = "저작권 개선 필요"
        else:
            draft["copyright_notes"] = "통과"
        
        # Step 4: 마케팅 강화
        print(f"\n[4/5] 💪 마케팅 요소 적용 중...")
        marketing = self.marketing.enhance_content(
            product_name=draft.get("product_name", keyword),
            category=draft.get("category", ""),
            price_range=draft.get("price_range", ""),
            specs=draft.get("specs", {}),
            pros=draft.get("pros", []),
            cons=draft.get("cons", []),
        )
        enhanced = self.marketing.apply_marketing_to_content(
            draft["title"], draft["content_sections"], marketing
        )
        enhanced["_raw_content"] = draft.get("content", "")
        draft["marketing"] = marketing
        draft["content"] = self._assemble_final_content(enhanced)
        
        # Step 5: 포스트 조립
        print(f"\n[5/5] 📦 최종 포스트 생성...")
        post = self._build_post(keyword, draft, copyright_result)
        
        # 저장
        self._save_draft(post)
        
        print(f"\n{'='*50}")
        print(f"✅ 생성 완료!")
        print(f"📄 제목: {post.title}")
        print(f"📁 상태: {post.status}")
        print(f"🔎 저작권: {post.review_notes}")
        print(f"{'='*50}")
        
        return post
    
    def _create_draft(self, keyword: str, research: ResearchResult) -> Dict:
        """
        LLM을 사용하여 콘텐츠 초안 생성
        실제로는 DeepSeek API를 호출
        """
        # LLM 프롬프트 구성
        prompt = self._build_generation_prompt(keyword, research)
        
        # 여기서는 구조적 결과를 반환 (실제 구현시 API 호출)
        draft = self._call_llm(prompt, keyword)
        
        return draft
    
    def _build_generation_prompt(self, keyword: str, research: ResearchResult) -> str:
        """콘텐츠 생성을 위한 LLM 프롬프트 구성 — 한국 인기 블로그 스타일 학습 적용"""
        config = self.config
        
        prompt = f"""당신은 한국에서 가장 성공적인 IT/디지털 제품 리뷰 블로그 '잇픽'의 전문 필자입니다.
아래의 **한국 수익형 블로그 글쓰기 공식**을 반드시 따라주세요.

═══════════════════════════════════════════
📌 한국형 리뷰 블로그 공식 (반드시 준수)
═══════════════════════════════════════════

## 1️⃣ 말투 & 톤
- 기본: **'-요'체** (가벼운 존댓말, 독자와 친근하게)
  예: "오늘은 가성비 노트북 5가지를 추천해드릴게요~
- 전문적인 부분은 **'-니다'체** 혼합 (신뢰감)
  예: "해당 제품의 벤치마크 점수는 다음과 같습니다"
- **개인적인 경험/의견**을 자연스럽게 넣을 것
  예: "제가 직접 3개월 써본 결과..."

## 2️⃣ 제목 공식
❌ "맥북 M4 프로 비교 분석" (재미없음)
✅ "2026년 맥북 M4 프로 입문자용 완벽 가이드🔥 가격부터 스펙까지 싹 정리!" (클릭 유도)
✅ "갤럭시 S26 살까? 아이폰 17 살까? 3개월 고민 후 내린 결론"
✅ "무선청소기 TOP 5 비교 [가격/성능/디자인 한눈에]"

## 3️⃣ 글 구조 (정해진 순서)
[1] 도입부 (15~20%):
   - 독자의 고통/고민 자극 ("노트북 고르다가 포기한 적 있나요?")
   - 또는 개인 경험 ("나는 2주간 10개 제품을 직접 써봤다")
   - 이 글을 읽으면 얻을 수 있는 것 약속

[2] 본론 (60%):
   - 각 제품별로 **제목 굵게** | 스펙 요약 | 장점 3개 | 단점 1~2개 | 추천 대상
   - 반드시 표로 스펙 비교
   - 핵심 포인트는 **볼드** 처리
   - 한 제품당 5~8줄, 너무 길지 않게

[3] 비교표 (10%):
   - 모든 제품을 한눈에 비교하는 표
   - 가격/성능/디자인/배터리/추천점수 별표(⭐) 평가

[4] 결론 (10~15%):
   - 상황별 최종 추천 (표로 정리)
   - "내 결론은..." 개인 의견 한 줄
   - 솔직한 총평 (단점도 포함)
   
## 4️⃣ 검색 SEO 패턴
- 키워드를 자연스럽게 여러 번 분산 배치
  예: "가성비 노트북을 찾는다면... 이 가성비 노트북의 장점은..."
- H2, H3 제목에 핵심 키워드 포함
- 이미지 alt 텍스트에 키워드 포함 (선택)

## 5️⃣ 구매 유도 패턴
- 단점도 솔직히 말할 것 → 신뢰도 상승
- "내돈내산" 느낌의 개인 경험담
- 가격 대비 가치를 강조할 것
- 마지막에 "지금 쿠팡에서 확인하기" CTA

## 6️⃣ 피해야 할 것
❌ **한자(漢字) 사용 절대 금지** — 예: 感想(X) → 느낌(O), 必須(X) → 반드시(O)
❌ "당신의 선택", "혁신적인 기술", "완벽한" → AI 티 남
❌ 너무 딱딱한 보고서 스타일
❌ 3줄 이상 연속되는 긴 문단 (모바일 가독성 DOWN)
❌ 특정 브랜드 비방

═══════════════════════════════════════════

## 작성 정보
- 주제: {keyword}
- 분량: {config['content']['min_words']}~{config['content']['max_words']}자
- 대상: 20~40대 한국인 일반 소비자
- 글쓴이: IT 리뷰 블로거 (개인 경험/의견 포함)
- 쿠팡 파트너스 링크 포함 가능

## 필수 포함
{'✅ 목차 (Table of Contents)' if config['content']['include_toc'] else ''}
{'✅ 제품 스펙 비교표 (Markdown 테이블)' if config['content']['include_comparison_table'] else ''}
{'✅ 각 제품의 장점/단점 (Pro/Con)' if config['content']['include_pros_cons'] else ''}
✅ 구매 가이드 / 상황별 추천
✅ 솔직한 평가 (단점도 객관적으로)
✅ 개인적인 사용 경험/느낌

## 주의사항
- 허위 정보나 과장 금지 (정확한 스펙과 가격만)
- 객관적인 사실에 기반할 것
- 저작권 침해 위험이 있는 타 블로그 문장 그대로 사용 금지
- "매우", "정말", "진짜" 같은 표현은 적당히 사용
"""
        return prompt
    
    def _call_llm(self, prompt: str, keyword: str = "") -> Dict:
        """
        LLM API 호출 (DeepSeek / OpenAI)
        실제 배포시 활성화
        """
        config = self.config
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        
        # API 키가 있으면 실제 API 호출, 없으면 Mock
        if api_key:
            try:
                import httpx
                if config["ai"]["provider"] == "deepseek":
                    url = "https://api.deepseek.com/v1/chat/completions"
                else:
                    url = "https://api.openai.com/v1/chat/completions"
                
                response = httpx.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": config["ai"]["model"],
                        "messages": [
                            {"role": "system", "content": "You are a professional tech review blogger."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": config["ai"]["temperature"],
                        "max_tokens": config["ai"]["max_tokens"]
                    },
                    timeout=60
                )
                result = response.json()
                content = result["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"  ⚠️ API 호출 실패 (Mock 사용): {e}")
                content = self._mock_llm_response(prompt)
        else:
            print(f"  ⚠️ API 키 없음 (Mock 사용)")
            content = self._mock_llm_response(prompt)
        
        # 응답 파싱
        return self._parse_llm_response(content, keyword)
    
    def _mock_llm_response(self, prompt: str) -> str:
        """키워드 기반 동적 Mock 응답 생성"""
        # 프롬프트에서 키워드 추출
        kw_match = re.search(r'주제:\s*(.+?)(?:\n|$)', prompt)
        keyword = kw_match.group(1).strip() if kw_match else "IT 제품"
        
        # 카테고리별 동적 콘텐츠
        category_keywords = {
            "노트북": ["맥북", "갤럭시북", "LG 그램", "레노버", "ASUS"],
            "스마트폰": ["아이폰", "갤럭시", "샤오미", "구글 픽셀"],
            "이어폰": ["에어팟", "갤럭시 버즈", "소니", "보스"],
            "청소기": ["다이슨", "로보락", "삼성 비스포크", "LG 코드제로"],
            "태블릿": ["아이패드", "갤럭시 탭", "레노버 탭"],
            "스피커": ["홈팟", "갤럭시 홈", "소니", "JBL"],
            "모니터": ["LG 울트라기어", "삼성 오디세이", "델"],
        }
        
        detected_category = "IT 제품"
        example_products = ["Product A", "Product B", "Product C", "Product D"]
        for cat, products in category_keywords.items():
            if cat in keyword or any(p in keyword for p in products):
                detected_category = cat
                example_products = products[:5]
                break
        
        product1, product2, product3 = example_products[:3] if len(example_products) >= 3 else (example_products[0], "Product B", "Product C")
        
        return f"""# 2026년 {keyword}: TOP 3 비교 추천

## 도입
{keyword}를 고를 때 가장 중요한 것은 나의 사용 패턴에 맞는 제품을 선택하는 것입니다. 다양한 제품이 출시되고 있지만, 어떤 제품이 진짜 가성비인지 알기 어렵죠. 이 글에서는 2026년 현재 구매할 수 있는 가장 핫한 {keyword} 3가지를 비교 분석했습니다.

---

## 🥇 1위: {product1} (약 139만원)

**스펙**
| 항목 | 사양 |
|------|------|
| 프로세서 | 최신형 고성능 칩 |
| 메모리 | 16GB / 32GB |
| 저장공간 | 512GB / 1TB |
| 배터리 | 최대 15시간 |
| 무게 | 1.2kg |

**장점**
- 강력한 성능으로 어떤 작업도 거뜬합니다
- 배터리 효율이 매우 뛰어나 하루 종일 사용 가능
- 가벼운 무게로 휴대성이 좋습니다

**단점**
- 가격대가 다소 높은 편
- 기본 모델의 저장공간이 부족할 수 있음

**추천 대상:** 성능과 휴대성을 모두 원하는 분

---

## 🥈 2위: {product2} (약 89만원)

**스펙**
| 항목 | 사양 |
|------|------|
| 프로세서 | 중급형 고성능 칩 |
| 메모리 | 16GB |
| 저장공간 | 512GB |
| 배터리 | 최대 12시간 |
| 무게 | 1.5kg |

**장점**
- 가격 대비 성능이 출중합니다
- 실용적인 스펙 구성
- 다양한 포트 지원

**단점**
- 디스플레이가 다소 아쉬움
- 빌드 퀄리티가 프리미엄급은 아님

**추천 대상:** 가성비를 중시하는 실용적인 소비자

---

## 🥉 3위: {product3} (약 59만원)

**스펙**
| 항목 | 사양 |
|------|------|
| 프로세서 | 보급형 칩 |
| 메모리 | 8GB / 16GB |
| 저장공간 | 256GB / 512GB |
| 배터리 | 최대 10시간 |
| 무게 | 1.8kg |

**장점**
- 매우 합리적인 가격
- 기본 사무/인터넷 용도로 충분한 성능
- 초보자에게 적합

**단점**
- 고사양 작업에는 부적합
- 디스플레이 품질이 낮은 편

**추천 대상:** 예산이 한정된 학생이나 가벼운 사용자

---

## 📊 최종 비교

| 제품 | 가격 | 성능 | 휴대성 | 가성비 |
|------|------|------|--------|--------|
| {product1} | 139만원 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| {product2} | 89만원 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| {product3} | 59만원 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 💡 구매 가이드

### 상황별 추천
| 상황 | 추천 제품 |
|------|-----------|
| 🎓 학생 / 예산 한정 | **{product3}** — 가격 부담 최소 |
| 💼 직장인 / 데일리 | **{product2}** — 가성비 최고 |
| 🎬 전문가 / 크리에이터 | **{product1}** — 최고의 성능 |

### 구매 전 체크리스트
1. 내가 주로 하는 작업이 무엇인가?
2. 예산은 어느 정도인가?
3. 휴대성이 중요한가?
4. 애프터서비스(AS) 정책은 괜찮은가?

---

*이 글은 2026년 7월 기준으로 작성되었습니다. 가격과 스펙은 변동될 수 있습니다.*
"""
    def _parse_llm_response(self, content: str, keyword: str = "") -> Dict:
        """LLM 응답을 구조화된 데이터로 파싱"""
        # 제목 추출
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else "제품 비교 추천"
        
        # 설명 추출 (첫 번째 문단)
        desc_match = re.search(r'^(?!^#)([^.]+\.)', content, re.MULTILINE)
        description = desc_match.group(1) if desc_match else f"{title}에 대한 상세 비교 리뷰"
        
        # 카테고리 추론 (키워드 기반)
        category = self._detect_category(keyword)
        
        return {
            "title": title,
            "description": description,
            "content": content,
            "content_sections": {
                "intro": content[:200] if len(content) > 200 else content,
            },
            "product_name": title.split("TOP")[0].strip() if "TOP" in title else title,
            "category": category,
            "price_range": "",
            "specs": {},
            "pros": [],
            "cons": [],
        }
    
    def _detect_category(self, keyword: str) -> str:
        """키워드에서 제품 카테고리 추론"""
        category_map = {
            "노트북": ["노트북", "랩탑", "맥북", "갤럭시 북", "그램"],
            "스마트폰": ["스마트폰", "핸드폰", "아이폰", "갤럭시", "폰"],
            "이어폰": ["이어폰", "헤드폰", "헤드셋", "에어팟", "버즈", "사운드"],
            "청소기": ["청소기", "로봇청소기", "무선청소기", "진공청소기"],
            "태블릿": ["태블릿", "아이패드", "갤럭시 탭", "패드"],
            "모니터": ["모니터", "디스플레이", "화면"],
            "키보드": ["키보드", "기계식"],
            "마우스": ["마우스"],
            "스피커": ["스피커", "블루투스 스피커", "사운드바"],
            "공기청정기": ["공기청정기", "에어클리너"],
            "세탁기": ["세탁기", "건조기"],
            "냉장고": ["냉장고", "김치냉장고"],
            "TV": ["TV", "티비", "텔레비전", "QLED", "OLED TV"],
        }
        for cat, keywords in category_map.items():
            for kw in keywords:
                if kw in keyword:
                    return cat
        return "IT 기기"
    
    def _assemble_final_content(self, enhanced: Dict) -> str:
        """마케팅 요소가 적용된 최종 콘텐츠 조립"""
        # 원본 콘텐츠를 최우선으로 사용
        raw_content = enhanced.get("_raw_content", "")
        if raw_content:
            content = raw_content
        else:
            # 여러 형식에서 추출 시도
            content = ""
            for key in ["content", "intro"]:
                if isinstance(enhanced.get("content"), dict):
                    content = enhanced["content"].get(key, content)
                    if content:
                        break
                elif isinstance(enhanced.get(key), str):
                    content = enhanced[key]
                    break
                elif isinstance(enhanced.get("content"), str):
                    content = enhanced["content"]
                    break
            if not content:
                content = "# 생성된 콘텐츠\n\n(내용 준비 중)"
        
        # 마케팅 뱃지 추가
        badges = []
        if isinstance(enhanced.get("content"), dict):
            badges = enhanced["content"].get("marketing_badges", [])
        if badges:
            badge_section = "\n\n---\n" + "\n".join([b["text"] for b in badges]) + "\n---\n"
            content += badge_section
        
        # CTA 추가
        marketing = enhanced.get("marketing_elements")
        if marketing and marketing.call_to_actions:
            content += f"\n\n---\n"
            content += f"\n💡 **{marketing.call_to_actions[0]}**\n"
        
        return content
    
    def _build_post(self, keyword: str, draft: Dict, 
                    copyright_v: CopyrightVerdict) -> GeneratedPost:
        """최종 포스트 객체 생성"""
        config = self.config
        now = datetime.now()
        
        # 발행일 (리뷰 후 발행 가능)
        pub_date = now + timedelta(days=1)
        
        # Slug 생성
        slug = self._make_slug(draft["title"])
        
        # 태그
        tags = [keyword, config["blog"]["name"]]
        
        # 최종 콘텐츠에 저작권 메모 추가 (검수용)
        review_notes = f"저작권 점수: {copyright_v.originality_score}/100"
        if copyright_v.flagged_phrases:
            review_notes += f"\n주의: {'; '.join(copyright_v.flagged_phrases[:3])}"
        if copyright_v.suggestions:
            review_notes += f"\n제안: {'; '.join(copyright_v.suggestions[:3])}"
        
        return GeneratedPost(
            title=draft["title"],
            description=draft.get("description", ""),
            slug=slug,
            tags=tags,
            content=draft["content"],
            hero_image="../../assets/blog-placeholder-1.jpg",
            pub_date=pub_date.strftime("%b %d %Y"),
            status="draft",
            review_notes=review_notes
        )
    
    def _make_slug(self, title: str) -> str:
        """제목 → URL 슬러그 변환"""
        slug = title.lower()
        slug = re.sub(r'[^a-z0-9가-힣\s-]', '', slug)
        slug = re.sub(r'[\s]+', '-', slug.strip())
        slug = re.sub(r'-+', '-', slug)
        return slug[:80]
    
    def _save_draft(self, post: GeneratedPost):
        """초안 저장"""
        filename = f"{post.slug}.md"
        filepath = self.drafts_dir / filename
        
        content = f"""---
title: '{post.title}'
description: '{post.description}'
pubDate: '{post.pub_date}'
heroImage: '{post.hero_image}'
tags: [{', '.join(f"'{t}'" for t in post.tags)}]
status: '{post.status}'
reviewNotes: '{post.review_notes}'
---

{post.content}
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"  📄 초안 저장: {filepath}")
    
    def list_drafts(self) -> List[Path]:
        """검수 대기중인 초안 목록"""
        return sorted(self.drafts_dir.glob("*.md"))
    
    def approve_post(self, slug: str) -> bool:
        """초안 승인 → 발행 대기"""
        draft_path = self.drafts_dir / f"{slug}.md"
        if not draft_path.exists():
            print(f"❌ 초안 없음: {slug}")
            return False
        
        # 프론트매터의 status 변경
        content = draft_path.read_text(encoding="utf-8")
        content = content.replace("status: 'draft'", "status: 'approved'")
        draft_path.write_text(content, encoding="utf-8")
        
        print(f"✅ 승인 완료: {slug}")
        return True
    
    def reject_post(self, slug: str, reason: str = ""):
        """초안 반려"""
        draft_path = self.drafts_dir / f"{slug}.md"
        if draft_path.exists():
            reject_path = self.rejected_dir / f"{slug}.md"
            draft_path.rename(reject_path)
            print(f"📁 반려: {slug} ({reason})")


def main():
    """CLI 진입점"""
    import sys
    
    pipeline = ContentPipeline()
    
    if len(sys.argv) < 2:
        print("사용법: python content_gen.py <키워드>")
        print("   또는: python content_gen.py --list")
        print("   또는: python content_gen.py --approve <slug>")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        drafts = pipeline.list_drafts()
        if drafts:
            print("\n📋 검수 대기중인 초안:")
            for d in drafts:
                print(f"  • {d.stem}")
        else:
            print("📭 검수 대기중인 초안이 없습니다.")
    
    elif sys.argv[1] == "--approve" and len(sys.argv) > 2:
        pipeline.approve_post(sys.argv[2])
    
    else:
        keyword = " ".join(sys.argv[1:])
        post = pipeline.generate(keyword)


if __name__ == "__main__":
    main()
