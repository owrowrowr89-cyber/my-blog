"""
Publisher Module - 승인된 콘텐츠 → GitHub 푸시 → 배포

Flow:
1. drafts/에서 승인된 포스트 확인
2. Astro content/blog/로 복사
3. Git 커밋 + 푸시
4. GitHub Actions에서 자동 배포
"""
import yaml
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional

class Publisher:
    """블로그 콘텐츠 발행 관리자"""
    
    def __init__(self):
        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        
        self.repo_path = Path(self.config["github"]["repo_path"])
        self.drafts_dir = Path(__file__).parent / "content" / "drafts"
        self.published_dir = Path(__file__).parent / "content" / "published"
        self.blog_content_dir = self.repo_path / self.config["github"]["content_dir"]
    
    def publish_approved(self, slug: Optional[str] = None, auto_push: bool = True) -> List[str]:
        """
        승인된 초안을 블로그에 발행
        
        Args:
            slug: 특정 슬러그만 발행 (None=전체)
            auto_push: Git 푸시 자동 실행
            
        Returns:
            발행된 포스트 슬러그 목록
        """
        published = []
        
        # 발행할 포스트 찾기
        if slug:
            draft_files = [self.drafts_dir / f"{slug}.md"]
        else:
            draft_files = sorted(self.drafts_dir.glob("*.md"))
        
        for draft_path in draft_files:
            if not draft_path.exists():
                print(f"❌ 파일 없음: {draft_path}")
                continue
            
            # 프론트매터 확인
            content = draft_path.read_text(encoding="utf-8")
            if "status: 'approved'" not in content:
                print(f"⏭️ 승인되지 않음: {draft_path.stem}")
                continue
            
            # Astro 블로그 콘텐츠 디렉토리로 복사
            target_path = self.blog_content_dir / draft_path.name
            target_path.write_text(content, encoding="utf-8")
            
            # 발행 완료 처리 (draft → published)
            moved_content = content.replace("status: 'approved'", "status: 'published'")
            published_path = self.published_dir / draft_path.name
            published_path.write_text(moved_content, encoding="utf-8")
            draft_path.unlink()  # draft 삭제
            
            published.append(draft_path.stem)
            print(f"✅ 발행 완료: {draft_path.stem} → {target_path}")
        
        # Git 푸시
        if published and auto_push:
            self._git_push(published)
        
        return published
    
    def _git_push(self, published_slugs: List[str]):
        """Git 커밋 + 푸시"""
        try:
            repo = str(self.repo_path)
            
            # Git add
            subprocess.run(
                ["git", "add", "-A"],
                cwd=repo,
                capture_output=True, text=True, check=True
            )
            
            # Git commit
            msg = f"📝 블로그 발행: {', '.join(published_slugs[:3])}"
            if len(published_slugs) > 3:
                msg += f" 외 {len(published_slugs) - 3}건"
            
            result = subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=repo,
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                # Git push
                push_result = subprocess.run(
                    ["git", "push"],
                    cwd=repo,
                    capture_output=True, text=True, timeout=30
                )
                if push_result.returncode == 0:
                    print(f"🚀 GitHub 푸시 완료! → 자동 배포 시작")
                else:
                    print(f"⚠️ Push 오류: {push_result.stderr}")
            else:
                if "nothing to commit" in result.stdout:
                    print("ℹ️ 커밋할 변경사항 없음")
                else:
                    print(f"⚠️ Commit 오류: {result.stderr}")
                    
        except subprocess.TimeoutExpired:
            print("⏱️ Git Push 시간 초과 (30초)")
        except Exception as e:
            print(f"⚠️ Git 오류: {e}")
    
    def schedule_posts(self, count: int = 2) -> List[str]:
        """
        다음 발행 예정인 포스트의 발행일을 조정
        
        최적 발행 시간(hour)에 맞춰 예약
        """
        config = self.config["publishing"]
        optimal_hour = config["optimal_hour"]
        interval = config["min_interval_minutes"]
        
        drafts = sorted(self.drafts_dir.glob("*.md"))
        scheduled = []
        
        now = datetime.now()
        next_pub = now.replace(hour=optimal_hour, minute=0, second=0)
        
        if next_pub < now:
            next_pub = next_pub.replace(day=next_pub.day + 1)
        
        for i, draft in enumerate(drafts[:count]):
            # 프론트매터 pubDate 업데이트
            content = draft.read_text(encoding="utf-8")
            new_date = next_pub.strftime("%b %d %Y")
            
            # 날짜 교체
            content = re.sub(
                r"pubDate: '.*?'",
                f"pubDate: '{new_date}'",
                content
            )
            draft.write_text(content, encoding="utf-8")
            scheduled.append(draft.stem)
            
            # 다음 발행 시간 (interval 분 후)
            next_pub = next_pub.replace(minute=next_pub.minute + interval)
            
            print(f"📅 예약: {draft.stem} → {new_date}")
        
        return scheduled


def main():
    import sys
    
    publisher = Publisher()
    
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python publisher.py              # 승인된 전체 발행")
        print("  python publisher.py <slug>       # 특정 글만 발행")
        print("  python publisher.py --schedule   # 발행 시간 예약")
        print("  python publisher.py --status     # 발행 상태 확인")
        sys.exit(1)
    
    if sys.argv[1] == "--schedule":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        publisher.schedule_posts(count)
    
    elif sys.argv[1] == "--status":
        drafts = list(publisher.drafts_dir.glob("*.md"))
        published = list(publisher.published_dir.glob("*.md"))
        print(f"📋 검수 대기: {len(drafts)}개")
        print(f"✅ 발행 완료: {len(published)}개")
        for d in drafts:
            print(f"  • {d.stem}")
    
    elif sys.argv[1].startswith("--"):
        print(f"❌ 알 수 없는 옵션: {sys.argv[1]}")
    
    else:
        publisher.publish_approved(slug=sys.argv[1])


if __name__ == "__main__":
    main()
