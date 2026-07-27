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
        """콘텐츠 생성을 위한 LLM 프롬프트 구성"""
        config = self.config
        
        prompt = f"""당신은 IT/디지털 제품 비교 리뷰 블로그 '잇픽'의 전문 필자입니다.
한국어로 블로그 글을 작성해주세요.

## 작성 조건
- 주제: {keyword}
- 분량: {config['content']['min_words']}~{config['content']['max_words']}자
- 톤: 전문적이면서도 친근한 말투, '-니다'체
- 대상: IT에 관심 있는 일반 소비자 (20~40대)

## 필수 포함 요소
{' - 목차 (Table of Contents)' if config['content']['include_toc'] else ''}
{' - 제품 스펙 비교표 (Markdown 테이블)' if config['content']['include_comparison_table'] else ''}
{' - 각 제품의 장점/단점' if config['content']['include_pros_cons'] else ''}
- 구매 가이드 / 추천 대상
- 솔직한 평가 (단점도 객관적으로)

## 작성 구조
1. 제목: 클릭하고 싶은 제목 (숫자 포함, 구체적으로)
2. 도입: 독자의 고민/문제 인식 → 이 글을 읽어야 하는 이유
3. 본론: 각 제품별 리뷰 (스펙, 장점, 단점, 추천 대상)
4. 비교표: 한눈에 비교할 수 있는 표
5. 결론: 상황별 최종 추천, 구매 링크

## 주의사항
- 허위 정보나 과장 금지 (정확한 스펙과 가격만)
- 특정 브랜드를 과도하게 비방하지 말 것
- 객관적인 사실에 기반할 것
- 저작권 침해 위험이 있는 타 블로그 문장 그대로 사용 금지
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
        """개발/테스트용 Mock 응답"""
        return f"""# 2025년 가성비 노트북 TOP 5 비교 추천

## 도입
노트북을 고를 때 가장 중요한 것은 가격 대비 성능입니다. 하지만 수많은 제품 중에서 진짜 가성비를 찾기 어렵죠. 이 글에서는 2025년 현재 구매할 수 있는 최고의 가성비 노트북 5가지를 가격대별로 정리했습니다.

## 1위: 레노버 아이디어패드 슬림 5 (약 69만원)
**스펙:** 라이젠 7 8845HS / 16GB RAM / 512GB SSD / 15.6형 FHD IPS

**장점:** 가격 대비 성능이 압도적입니다. AMD 내장 그래픽이 생각보다 강력해서 가벼운 게임도 가능합니다. 

**단점:** 디스플레이 밝기가 300nit로 야외 사용은 다소 부족합니다.

**추천 대상:** 예산이 한정된 대학생, 사무용으로 충분한 성능을 원하는 분

## 2위: 맥북 에어 M4 (약 119만원)
**스펙:** Apple M4 / 16GB RAM / 256GB SSD / 13.6형 Liquid Retina

**장점:** 배터리가 진짜 하루 종일 가고, M4 칩의 성능이 인텔/AMD를 압도합니다.

**단점:** 저장공간 256GB는 부족할 수 있고, 윈도우 전용 프로그램이 필요하면 불편합니다.

## 비교표
| 제품 | 가격 | CPU | RAM | 디스플레이 |
|------|------|-----|-----|-----------|
| 아이디어패드 슬림 5 | 69만 | R7 8845HS | 16GB | FHD IPS |
| 맥북 에어 M4 | 119만 | M4 | 16GB | Liquid Retina |

## 최종 추천
당신의 상황에 맞는 최고의 선택을 찾으세요.
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
        # 기본 콘텐츠 — 여러 형식에서 추출 시도
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
            # draft 객체에서 content 가져오기
            content = enhanced.get("_raw_content", "# 생성된 콘텐츠\n\n(내용 준비 중)")
        
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
