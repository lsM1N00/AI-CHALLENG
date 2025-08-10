import requests
from bs4 import BeautifulSoup
import time
import json
import csv
from datetime import datetime
import os

def parse_fss_detail_page(html):
    soup = BeautifulSoup(html, "html.parser")

    # bd-view 컨테이너 찾기
    bd_view = soup.select_one("div.bd-view")
    
    if bd_view:
        # 제목 추출
        title_tag = bd_view.select_one("h2.subject")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # 본문 추출
        body_div = bd_view.select_one("div.dbdata")
        if body_div:
            # <p>, <span> 등을 모두 텍스트로 병합
            body = body_div.get_text(separator="\n", strip=True)
        else:
            body = ""
    else:
        # bd-view가 없는 경우 전체 페이지에서 찾기
        title_tag = soup.select_one("h2.subject")
        title = title_tag.get_text(strip=True) if title_tag else ""

        body_div = soup.select_one("div.dbdata")
        if body_div:
            body = body_div.get_text(separator="\n", strip=True)
        else:
            body = ""

    return title, body


def fss_faq(urls, max_pages=95):
    """
    FSS FAQ 크롤링 함수 - 여러 URL 지원 + 페이지네이션
    
    Args:
        urls: URL 리스트 또는 단일 URL 문자열
        max_pages: 각 URL당 최대 페이지 수 (기본값: 95)
    """
    # URL이 문자열인 경우 리스트로 변환
    if isinstance(urls, str):
        urls = [urls]
    
    # User-Agent (봇으로 차단되지 않도록 설정)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    all_faq_list = []
    
    for url in urls:
        print(f"🔍 FSS FAQ 크롤링 중: {url}")
        faq_list = []
        
        try:
                        # 페이지별로 크롤링
            for page in range(1, max_pages + 1):
                print(f"  📄 페이지 {page} 처리 중...")

                if "?" in url:
                    page_url = f"{url}&pageIndex={page}"
                else:
                    page_url = f"{url}?pageIndex={page}"

                res = requests.get(page_url, headers=headers)
                soup = BeautifulSoup(res.text, "html.parser")

                rows = soup.select("tbody > tr")  # ✅ 테이블 행 기준으로 변경
                if not rows:
                    print(f"    ⚠️ 페이지 {page}에 FAQ 목록이 없습니다.")
                    break

                page_faq_count = 0
                for row in rows:
                    try:
                        title_tag = row.select_one("td.title a")
                        if not title_tag:
                            continue  # 유효하지 않은 항목

                        title = title_tag.get_text(strip=True)
                        href = title_tag["href"]

                        if not href or href.startswith("javascript"):
                            continue

                        # 상대경로 → 절대경로
                        if href.startswith("/"):
                            link = "https://www.fss.or.kr" + href
                        else:
                            link = href

                        # 상세 페이지 접근
                        detail_res = requests.get(link, headers=headers)
                        question_title, body = parse_fss_detail_page(detail_res.text)

                        if body.strip():
                            faq_list.append({
                                "title": question_title or title,
                                "body": body,
                                "url": link,
                                "source_url": url,
                                "page": page
                            })
                            page_faq_count += 1
                            time.sleep(0.5)

                    except Exception as e:
                        print(f"    ⚠️ 항목 처리 오류: {e}")
                        continue

                print(f"    ✅ 페이지 {page}에서 {page_faq_count}개 수집 완료")
                time.sleep(1)
            
            all_faq_list.extend(faq_list)
            print(f"✅ {url}에서 총 {len(faq_list)}개의 FAQ 수집 완료")
            
        except Exception as e:
            print(f"❌ URL 처리 중 오류 발생: {url}, 오류: {e}")
            continue

    # 결과 예시 출력
    print(f"\n📊 총 {len(all_faq_list)}개의 FAQ 수집 완료")
    for i, faq in enumerate(all_faq_list[:3]):
        print(f"\n[{i+1}] {faq['title']}")
        print(f"URL: {faq['url']}")
        print(f"페이지: {faq.get('page', 'N/A')}")
        print(f"본문:\n{faq['body'][:300]}...")

    return all_faq_list


def kbstar_faq(urls, max_pages=7):
    """
    KB스타 FAQ 크롤링 함수 - 여러 URL 지원 + 페이지네이션
    
    Args:
        urls: URL 리스트 또는 단일 URL 문자열
        max_pages: 각 URL당 최대 페이지 수 (기본값: 10)
    """
    # URL이 문자열인 경우 리스트로 변환
    if isinstance(urls, str):
        urls = [urls]
    
    # User-Agent (봇으로 차단되지 않도록 설정)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    all_faq_list = []
    
    for url in urls:
        print(f"🔍 KB스타 FAQ 크롤링 중: {url}")
        faq_list = []
        
        try:
            # 페이지별로 크롤링
            for page in range(1, max_pages + 1):
                print(f"  📄 페이지 {page} 처리 중...")
                
                # 페이지 파라미터 추가
                if "?" in url:
                    page_url = f"{url}&pageIndex={page}"
                else:
                    page_url = f"{url}?pageIndex={page}"
                
                res = requests.get(page_url, headers=headers)
                soup = BeautifulSoup(res.text, "html.parser")
                
                # KB스타 사이트에 맞는 다양한 선택자 시도
                selectors = [
                    "td.left > a",  # 실제 KB스타 FAQ 링크 구조
                    "td a",  # td 안의 a 태그
                    ".left a",  # left 클래스 안의 a 태그
                    "a[href*='quics']",  # quics가 포함된 href를 가진 a 태그
                    ".faq-list li", 
                    ".bbs-list li", 
                    ".list-item",
                    ".faq-item",
                    ".item",
                    "li a",  # 모든 li 안의 a 태그
                    ".content a",  # content 클래스 안의 a 태그
                ]
                
                items = []
                for selector in selectors:
                    items = soup.select(selector)
                    if items:
                        print(f"    ✅ 선택자 '{selector}'로 {len(items)}개 항목 발견")
                        break
                
                if not items:
                    print(f"    ⚠️ 페이지 {page}에서 FAQ 항목을 찾을 수 없습니다.")
                    print(f"    🔍 페이지 HTML 구조 확인 중...")
                    
                    # 페이지 내용 일부 출력 (디버깅용)
                    page_content = soup.get_text()[:500]
                    print(f"    📄 페이지 내용 일부: {page_content}...")
                    
                    # 더 이상 페이지가 없으면 중단
                    if page > 1:
                        break
                    continue
                
                page_faq_count = 0
                for item in items:
                    try:
                        # FAQ 링크에서 제목과 href 추출
                        title = item.get_text(strip=True)
                        href = item.get("href", "")
                        
                        # 디버깅: 첫 번째 항목의 정보 출력
                        if page_faq_count == 0:
                            print(f"    🔍 첫 번째 FAQ 링크 정보:")
                            print(f"      제목: {title}")
                            print(f"      href: {href}")
                        
                        # href가 비어있거나 의미없는 링크인지 확인
                        if not href or href == "#" or href == "javascript:void(0)":
                            continue
                        
                        # 상대 경로를 절대 경로로 변환
                        if href.startswith("/"):
                            link = "https://obank.kbstar.com" + href
                        elif href.startswith("http"):
                            link = href
                        else:
                            link = "https://obank.kbstar.com/" + href

                        # 디버깅: 최종 링크 출력
                        if page_faq_count == 0:
                            print(f"      최종 링크: {link}")

                        # 상세 페이지 접근
                        detail_res = requests.get(link, headers=headers)
                        detail_soup = BeautifulSoup(detail_res.text, "html.parser")
                        
                        # 상세 페이지에서 질문과 답변 추출 (dl.faq_view 구조)
                        faq_view = detail_soup.select_one("dl.faq_view")
                        
                        if faq_view:
                            question_element = faq_view.select_one("dt strong")
                            answer_element = faq_view.select_one("dd.cont #view_cont")
                            
                            if question_element and answer_element:
                                question_title = question_element.get_text(strip=True)
                                body = answer_element.get_text(strip=True, separator="\n")
                                
                                # 디버깅: 첫 번째 FAQ 상세 정보 출력
                                if page_faq_count == 0:
                                    print(f"      질문: {question_title}")
                                    print(f"      답변 길이: {len(body)}자")
                                
                                if body.strip():
                                    faq_list.append({
                                        "title": question_title,  # 상세 페이지의 질문 제목 사용
                                        "body": body,
                                        "url": link,
                                        "source_url": url,
                                        "page": page
                                    })
                                    
                                    page_faq_count += 1
                                    time.sleep(0.5)  # 서버 과부하 방지
                                
                        else:
                            # dl.faq_view 구조가 없는 경우 다른 선택자 시도
                            content_selectors = [
                                "#view_cont",  # 실제 KB스타 구조
                                ".faq-content", 
                                ".bbs-view-contents", 
                                ".content-area",
                                ".content",
                                ".text",
                                ".body"
                            ]
                            
                            content = None
                            for content_selector in content_selectors:
                                content = detail_soup.select_one(content_selector)
                                if content:
                                    break
                            
                            body = content.get_text(strip=True, separator="\n") if content else ""

                            # 본문이 비어있으면 건너뛰기
                            if not body.strip():
                                if page_faq_count == 0:
                                    print(f"      ⚠️ 본문이 비어있습니다.")
                                continue

                            faq_list.append({
                                "title": title,  # 목록 페이지의 제목 사용
                                "body": body,
                                "url": link,
                                "source_url": url,
                                "page": page
                            })
                            
                            page_faq_count += 1
                            time.sleep(0.5)  # 서버 과부하 방지
                        
                    except Exception as e:
                        print(f"    ⚠️ 개별 FAQ 처리 중 오류: {e}")
                        continue
                
                print(f"    ✅ 페이지 {page}에서 {page_faq_count}개의 FAQ 수집")
                
                # 페이지 간 딜레이
                time.sleep(1)
            
            all_faq_list.extend(faq_list)
            print(f"✅ {url}에서 총 {len(faq_list)}개의 FAQ 수집 완료")
            
        except Exception as e:
            print(f"❌ URL 처리 중 오류 발생: {url}, 오류: {e}")
            continue

    # 결과 예시 출력
    print(f"\n📊 총 {len(all_faq_list)}개의 FAQ 수집 완료")
    for i, faq in enumerate(all_faq_list[:3]):
        print(f"\n[{i+1}] {faq['title']}")
        print(f"URL: {faq['url']}")
        print(f"페이지: {faq.get('page', 'N/A')}")
        print(f"본문:\n{faq['body'][:300]}...")

    return all_faq_list


def save_to_jsonl(data, filename):
    """
    데이터를 JSONL 파일로 저장합니다.
    각 줄은 {"instruction": title, "input": "", "output": body} 형식입니다.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for item in data:
                jsonl_item = {
                    "instruction": item["title"],
                    "input": "",
                    "output": item["body"]
                }
                f.write(json.dumps(jsonl_item, ensure_ascii=False) + '\n')
        print(f"데이터가 {filename}에 JSONL 형식으로 저장되었습니다.")
    except Exception as e:
        print(f"JSONL 파일 저장 중 오류 발생: {e}")


def save_to_json(data, filename):
    """
    데이터를 JSON 파일로 저장합니다.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"데이터가 {filename}에 저장되었습니다.")
    except Exception as e:
        print(f"JSON 파일 저장 중 오류 발생: {e}")


def save_to_csv(data, filename):
    """
    데이터를 CSV 파일로 저장합니다.
    """
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ["title", "body", "url", "source_url", "page"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"데이터가 {filename}에 저장되었습니다.")
    except Exception as e:
        print(f"CSV 파일 저장 중 오류 발생: {e}")


def main():
    # FSS FAQ URL들 (여러 URL 추가 가능)
    fss_urls = [
        "https://www.fss.or.kr/fss/bbs/B0000172/list.do?menuNo=200202&bbsId=&cl1Cd=&cl2Cd=&cl3Cd=&pageIndex=1&paramDeptname=&viewType=&selectDeptname=&searchCnd=22&searchWrd="
    ]
    
    # 페이지 수 설정 (원하는 페이지 수로 변경 가능)
    max_pages = 95  # 각 URL당 최대 10페이지까지 크롤링
    
    # FSS FAQ 크롤링 (여러 URL 지원 + 페이지네이션)
    print(f"🏛️ 금융감독원 FAQ 크롤링 시작... (최대 {max_pages}페이지)")
    fss_faq_data = fss_faq(fss_urls, max_pages=max_pages)

    # 현재 날짜로 폴더 생성
    current_date = datetime.now().strftime("%Y%m%d")
    output_dir = f"faq_data_{current_date}"
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n📊 총 {len(fss_faq_data)}개의 FSS FAQ 데이터 수집 완료")

    # JSONL 파일로 저장 (instruction: title, input: "", output: body)
    save_to_jsonl(fss_faq_data, os.path.join(output_dir, "fss_faq.jsonl"))

    # JSON 파일로 저장
    save_to_json(fss_faq_data, os.path.join(output_dir, "fss_faq.json"))

    # CSV 파일로 저장
    save_to_csv(fss_faq_data, os.path.join(output_dir, "fss_faq.csv"))

if __name__ == "__main__":
    main()