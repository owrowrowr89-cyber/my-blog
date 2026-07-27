#!/usr/bin/env python3
"""
잇픽 블로그 자동화 파이프라인 - 메인 CLI

사용법:
  python pipeline.py 생성 "가성비 노트북 추천"    # 콘텐츠 생성
  python pipeline.py 목록                         # 검수 대기 목록
  python pipeline.py 승인 <slug>                  # 초안 승인
  python pipeline.py 발행 [slug]                  # 발행 (Git 푸시)
  python pipeline.py 예약 [개수]                  # 발행 예약
  python pipeline.py 상태                         # 전체 상태
"""
from typing import Optional
import sys
import json
from pathlib import Path
from datetime import datetime

# 모듈 import
from content_gen import ContentPipeline
from publisher import Publisher


class BlogPipeline:
    """블로그 자동화 파이프라인 통합 CLI"""
    
    def __init__(self):
        self.content = ContentPipeline()
        self.publisher = Publisher()
    
    def generate(self, keyword: str):
        """키워드 → 블로그 글 생성"""
        print(f"\n🚀 블로그 글 생성 시작")
        print(f"   키워드: {keyword}")
        print(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("-" * 40)
        
        post = self.content.generate(keyword)
        
        print(f"\n📋 생성 결과")
        print(f"   제목: {post.title}")
        print(f"   슬러그: {post.slug}")
        print(f"   상태: {post.status}")
        print(f"   검수노트: {post.review_notes}")
        print(f"\n👉 검수하려면: python pipeline.py 승인 {post.slug}")
        print(f"😡 반려하려면: python pipeline.py 반려 {post.slug}")
    
    def list_drafts(self):
        """검수 대기 목록"""
        drafts = self.content.list_drafts()
        
        print(f"\n📋 검수 대기 목록 ({len(drafts)}개)")
        print("-" * 40)
        
        if not drafts:
            print("   📭 검수 대기중인 글이 없습니다.")
            return
        
        for i, draft in enumerate(drafts, 1):
            content = draft.read_text(encoding="utf-8")
            
            # 프론트매터 파싱
            title = "???"
            status = "unknown"
            review = ""
            for line in content.split('\n')[:10]:
                if line.startswith("title:"):
                    title = line.split("'")[1] if "'" in line else line[7:].strip()
                elif "status:" in line:
                    status = line.split("'")[1] if "'" in line else "unknown"
                elif "reviewNotes:" in line:
                    review = line.split("'")[1] if "'" in line else ""
            
            print(f"  {i}. {title}")
            print(f"     📄 {draft.stem}")
            print(f"     🏷️  상태: {status}")
            if review:
                print(f"     🔍 {review[:80]}")
            print()
    
    def approve(self, slug: str):
        """초안 승인"""
        success = self.content.approve_post(slug)
        if success:
            print(f"\n✅ '{slug}' 승인 완료!")
            print(f"👉 발행하려면: python pipeline.py 발행")
    
    def reject(self, slug: str, reason: str = ""):
        """초안 반려"""
        self.content.reject_post(slug, reason)
        print(f"\n📁 '{slug}' 반려됨")
    
    def publish(self, slug: Optional[str] = None):
        """승인된 글 → 블로그 발행"""
        print(f"\n🚀 블로그 발행 시작")
        print("-" * 40)
        
        published = self.publisher.publish_approved(slug=slug)
        
        if published:
            print(f"\n✅ {len(published)}개 포스트 발행 완료!")
            print(f"   GitHub Actions → 자동 배포 중... (1~2분)")
        else:
            print("\n⚠️ 발행할 승인된 글이 없습니다.")
            print(f"   먼저 승인: python pipeline.py 승인 <slug>")
    
    def schedule(self, count: int = 2):
        """발행 예약 (최적 시간 설정)"""
        print(f"\n📅 발행 예약: {count}개")
        print("-" * 40)
        self.publisher.schedule_posts(count)
    
    def status(self):
        """전체 상태 조회"""
        drafts = list(self.content.drafts_dir.glob("*.md"))
        approved = [d for d in drafts if "status: 'approved'" in d.read_text(encoding="utf-8")]
        published = list(self.content.published_dir.glob("*.md"))
        blog_posts = list(self.publisher.blog_content_dir.glob("*.md"))
        
        print(f"\n📊 블로그 상태")
        print("-" * 40)
        print(f"   📝 검수 대기:  {len(drafts)}개")
        print(f"   ✅ 승인 완료:  {len(approved)}개")
        print(f"   📚 발행 완료:  {len(published)}개")
        print(f"   🌐 블로그 글: {len(blog_posts)}개")
        print()
        print(f"   ⚡ 다음 명령어:")
        print(f"      목록 보기:  python pipeline.py 목록")
        print(f"      글 생성:    python pipeline.py 생성 <키워드>")
        print(f"      검수 후:    python pipeline.py 승인 <slug>")
        print(f"      발행:       python pipeline.py 발행")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    pipeline = BlogPipeline()
    command = sys.argv[1]
    
    if command in ["생성", "create", "generate"]:
        if len(sys.argv) < 3:
            print("❌ 키워드를 입력하세요.")
            print("   예: python pipeline.py 생성 '가성비 노트북 추천'")
            sys.exit(1)
        keyword = " ".join(sys.argv[2:])
        pipeline.generate(keyword)
    
    elif command in ["목록", "list", "ls"]:
        pipeline.list_drafts()
    
    elif command in ["승인", "approve"]:
        if len(sys.argv) < 3:
            print("❌ 슬러그(slug)를 입력하세요.")
            print("   예: python pipeline.py 승인 2025년-가성비-노트북-top-5")
            sys.exit(1)
        pipeline.approve(sys.argv[2])
    
    elif command in ["반려", "reject"]:
        if len(sys.argv) < 3:
            print("❌ 슬러그(slug)를 입력하세요.")
            sys.exit(1)
        reason = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        pipeline.reject(sys.argv[2], reason)
    
    elif command in ["발행", "publish"]:
        slug = sys.argv[2] if len(sys.argv) > 2 else None
        pipeline.publish(slug)
    
    elif command in ["예약", "schedule"]:
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        pipeline.schedule(count)
    
    elif command in ["상태", "status"]:
        pipeline.status()
    
    else:
        print(f"❌ 알 수 없는 명령어: {command}")
        print()
        print(__doc__)


if __name__ == "__main__":
    main()
