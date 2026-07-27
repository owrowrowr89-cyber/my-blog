#!/usr/bin/env python3
"""
Auto Scheduler - 완전 자동 블로그 운영 시스템

아무것도 안 해도 됩니다. 이 스크립트가:
1. 트렌드 스캔 → 핫한 주제 선정
2. AI 콘텐츠 생성 (저작권 검증 + 마케팅 강화)
3. 초안 저장 (people-in-the-loop)
4. 승인된 글은 자동 발행

사용법:
  python auto_scheduler.py              # 1사이클 실행 (트렌드 → 생성)
  python auto_scheduler.py --full-auto  # 생성 → 승인 → 발행까지 한번에
  python auto_scheduler.py --daily      # 일일 정기 실행용
"""
import sys
import json
import random
from pathlib import Path
from datetime import datetime

from trend_scanner import TrendScanner
from content_gen import ContentPipeline
from publisher import Publisher


class AutoScheduler:
    """완전 자동 블로그 스케줄러"""
    
    def __init__(self):
        self.scanner = TrendScanner()
        self.pipeline = ContentPipeline()
        self.publisher = Publisher()
    
    def run_cycle(self, auto_publish: bool = False):
        """
        한 사이클 실행: 트렌드 분석 → 콘텐츠 생성 (→ 발행)
        
        Args:
            auto_publish: True면 생성→승인→발행 자동 처리
        """
        print(f"\n{'='*60}")
        print(f"🤖 블로그 자동화 사이클 시작")
        print(f"📅 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*60}")
        
        # Step 1: 트렌드 스캔
        print("\n📡 [Step 1] 트렌드 스캔...")
        report = self.scanner.scan_all()
        
        if not report.topics:
            print("❌ 트렌드 주제를 찾지 못했습니다.")
            return
        
        # Step 2: 발행할 주제 선정
        print(f"\n🎯 [Step 2] 발행할 주제 선정...")
        
        # 1) 이미 발행한 글 제외
        existing = set()
        for f in self.publisher.blog_content_dir.glob("*.md"):
            content = f.read_text(encoding="utf-8")
            if "title:" in content:
                for line in content.split('\n'):
                    if line.startswith("title:"):
                        existing.add(line.split("'")[1] if "'" in line else "")
        
        available = [t for t in report.topics if t.keyword not in existing]
        
        if not available:
            print("  모든 주제가 이미 발행됨. 새 주제 대기 중...")
            return
        
        # 점수 높은 순 + 약간의 랜덤성 (다양성)
        candidates = available[:5]
        selected = candidates[0]  # 기본적으로 1순위
        
        # 가끔은 2~3순위도 선택 (다양성)
        if len(candidates) > 2 and random.random() < 0.3:
            selected = random.choice(candidates[1:3])
        
        print(f"  선택: [{selected.category}] {selected.keyword}")
        print(f"  점수: {selected.score}, 출처: {selected.source}")
        
        # Step 3: 콘텐츠 생성
        print(f"\n✍️ [Step 3] 콘텐츠 생성...")
        post = self.pipeline.generate(selected.keyword)
        
        print(f"\n📝 생성 결과:")
        print(f"  제목: {post.title}")
        print(f"  상태: {post.status}")
        print(f"  저작권: {post.review_notes[:60]}...")
        
        # Step 4: 자동 발행 (auto_publish=True)
        if auto_publish:
            print(f"\n🚀 [Step 4] 자동 발행...")
            self.pipeline.approve_post(post.slug)
            published = self.publisher.publish_approved(slug=post.slug)
            if published:
                print(f"  ✅ '{post.title}' 블로그에 발행 완료!")
            else:
                print(f"  ⚠️ 발행 실패")
        else:
            print(f"\n⏸️  초안 상태로 대기 중")
            print(f"  검수하려면: python pipeline.py 승인 {post.slug}")
            print(f"  발행하려면: python pipeline.py 발행 {post.slug}")
        
        print(f"\n{'='*60}")
        print(f"✅ 사이클 완료!")
        print(f"{'='*60}")
    
    def daily_run(self):
        """
        일일 정기 실행: 하루 2포스트 생성
        
        - 오전 9시: 1개 생성 (검수 대기)
        - 오후 2시: 1개 생성 + 승인된 글 발행
        """
        hour = datetime.now().hour
        
        if 8 <= hour < 12:
            # 오전: 생성만
            print("🌅 오전 모드: 콘텐츠 생성 (검수 대기)")
            self.run_cycle(auto_publish=False)
        
        elif 13 <= hour < 17:
            # 오후: 생성 + 발행
            print("🌤️ 오후 모드: 생성 + 발행")
            self.run_cycle(auto_publish=True)
        
        else:
            # 그 외 시간: 기본 모드
            print("🌙 일반 모드")
            self.run_cycle(auto_publish=False)


def main():
    scheduler = AutoScheduler()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--full-auto":
            scheduler.run_cycle(auto_publish=True)
        elif sys.argv[1] == "--daily":
            scheduler.daily_run()
        else:
            print(f"❌ 알 수 없는 옵션: {sys.argv[1]}")
            print("사용법: python auto_scheduler.py [--full-auto | --daily]")
    else:
        scheduler.run_cycle(auto_publish=False)


if __name__ == "__main__":
    main()
