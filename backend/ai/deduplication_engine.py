import re
import hashlib
import json
from typing import List, Dict, Tuple, Any, Set
from urllib.parse import urlparse, parse_qs, urlunparse
from difflib import SequenceMatcher
from models import Job

# 64 deterministic hash permutations for MinHash signature computation
NUM_HASHES = 64
PRIME_MOD = 2147483647
HASH_SEEDS_A = [(i * 2654435761 + 1013904223) % PRIME_MOD for i in range(1, NUM_HASHES + 1)]
HASH_SEEDS_B = [(i * 1597334677 + 2860486313) % PRIME_MOD for i in range(1, NUM_HASHES + 1)]

SOURCE_PRIORITY = {
    "company_careers": 100,
    "greenhouse": 95,
    "lever": 95,
    "ashby": 95,
    "workable": 90,
    "adzuna": 60,
    "jooble": 50,
    "manual_import": 40,
    "search": 30
}

def get_source_rank(job: Job) -> int:
    url_lower = job.url.lower()
    
    if "greenhouse.io" in url_lower or "lever.co" in url_lower or "ashbyhq.com" in url_lower or "workable.com" in url_lower:
        return SOURCE_PRIORITY["company_careers"]
    if "adzuna" in url_lower:
        return SOURCE_PRIORITY["adzuna"]
    if "jooble" in url_lower:
        return SOURCE_PRIORITY["jooble"]
    if "manual" in url_lower:
        return SOURCE_PRIORITY["manual_import"]
    return SOURCE_PRIORITY.get(job.status.lower(), 30)

def clean_canonical_url(url: str) -> str:
    """Strips query tracking parameters and standardizes scheme/host/path."""
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip('/')
        
        # Filter tracking query parameters
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'ref', 'source', 'gh_jid', 'lever-origin', 'gclid', 'fbclid', 'submission_id'
        }
        query_dict = parse_qs(parsed.query)
        filtered_query = [(k, v) for k, v in query_dict.items() if k.lower() not in tracking_params]
        
        # Sort query keys for consistent hashing
        filtered_query.sort(key=lambda x: x[0])
        query_str = '&'.join([f"{k}={v[0]}" for k, v in filtered_query])
        
        return urlunparse((scheme, netloc, path, '', query_str, ''))
    except Exception:
        return url.strip().lower()

def compute_url_hash(url: str) -> str:
    canonical = clean_canonical_url(url)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest() if canonical else ""

def compute_title_company_hash(title: str, company: str) -> str:
    clean_t = re.sub(r'[^a-z0-9]', '', title.lower())
    clean_c = re.sub(r'[^a-z0-9]', '', company.lower())
    combined = f"{clean_c}:{clean_t}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()

def get_text_shingles(text: str, k: int = 3) -> Set[str]:
    """Extracts character k-gram shingles from text."""
    clean_text = re.sub(r'\s+', ' ', text.lower().strip())
    clean_text = re.sub(r'[^a-z0-9 ]', '', clean_text)
    if len(clean_text) < k:
        return {clean_text} if clean_text else set()
    return {clean_text[i:i+k] for i in range(len(clean_text) - k + 1)}

def compute_minhash_signature(text: str) -> List[int]:
    """Generates a 64-integer MinHash signature for text content."""
    shingles = get_text_shingles(text)
    if not shingles:
        return [0] * NUM_HASHES
    
    signature = []
    shingle_hashes = [int(hashlib.md5(s.encode('utf-8')).hexdigest(), 16) % PRIME_MOD for s in shingles]
    
    for i in range(NUM_HASHES):
        a = HASH_SEEDS_A[i]
        b = HASH_SEEDS_B[i]
        min_val = min((a * h + b) % PRIME_MOD for h in shingle_hashes)
        signature.append(min_val)
        
    return signature

def calculate_minhash_jaccard(sig1: List[int], sig2: List[int]) -> float:
    """Calculates estimated Jaccard similarity between two MinHash signatures."""
    if not sig1 or not sig2 or len(sig1) != len(sig2):
        return 0.0
    matches = sum(1 for a, b in zip(sig1, sig2) if a == b)
    return matches / len(sig1)

def token_set_similarity(str1: str, str2: str) -> float:
    tokens1 = set(re.findall(r'\w+', str1.lower()))
    tokens2 = set(re.findall(r'\w+', str2.lower()))
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union)

class MultiStageDeduplicator:
    """
    Multi-stage high-throughput deduplication engine for job listings.
    
    Stage 1: Canonical URL & Exact Hash Matching
    Stage 2: MinHash / Jaccard Text Shingle Similarity (>80% similarity threshold)
    Stage 3: Token Set Fuzzy Title & Company Grouping
    """
    def __init__(self, jaccard_threshold: float = 0.80, title_fuzzy_threshold: float = 0.82):
        self.jaccard_threshold = jaccard_threshold
        self.title_fuzzy_threshold = title_fuzzy_threshold

    def deduplicate(self, jobs: List[Job]) -> Tuple[List[Job], int]:
        if not jobs:
            return [], 0
            
        initial_count = len(jobs)
        
        # 1. Prepare job metadata (hashes & MinHash signatures)
        job_meta = []
        for j in jobs:
            url_h = compute_url_hash(j.url)
            tc_h = compute_title_company_hash(j.title, j.company)
            minhash_sig = compute_minhash_signature(j.description)
            job_meta.append({
                "job": j,
                "url_hash": url_h,
                "tc_hash": tc_h,
                "minhash_sig": minhash_sig,
                "rank": (get_source_rank(j), j.match_score, j.validation_score)
            })
            
        # 2. Stage 1: Group by Exact URL Hash or Title+Company Hash
        seen_urls = set()
        stage1_dedup = []
        
        for item in job_meta:
            u_hash = item["url_hash"]
            if u_hash and u_hash in seen_urls:
                continue
            if u_hash:
                seen_urls.add(u_hash)
            stage1_dedup.append(item)
            
        # 3. Stage 2 & 3: Fuzzy MinHash & Title Grouping by Company
        by_company: Dict[str, List[Dict[str, Any]]] = {}
        for item in stage1_dedup:
            comp_clean = re.sub(r'[^a-z0-9]', '', item["job"].company.lower().strip())
            if comp_clean not in by_company:
                by_company[comp_clean] = []
            by_company[comp_clean].append(item)
            
        final_selected = []
        
        for comp, items in by_company.items():
            clusters: List[List[Dict[str, Any]]] = []
            
            for item in items:
                matched_cluster = None
                for cluster in clusters:
                    representative = cluster[0]
                    
                    # Title Similarity Check
                    t1 = representative["job"].title.lower()
                    t2 = item["job"].title.lower()
                    t_sim = SequenceMatcher(None, t1, t2).ratio()
                    tok_sim = token_set_similarity(t1, t2)
                    
                    # MinHash Description Similarity Check
                    jaccard_sim = calculate_minhash_jaccard(representative["minhash_sig"], item["minhash_sig"])
                    
                    if t_sim >= self.title_fuzzy_threshold or tok_sim >= 0.85 or jaccard_sim >= self.jaccard_threshold:
                        matched_cluster = cluster
                        break
                        
                if matched_cluster is not None:
                    matched_cluster.append(item)
                else:
                    clusters.append([item])
                    
            # Pick best candidate per cluster based on rank score
            for cluster in clusters:
                cluster.sort(key=lambda x: x["rank"], reverse=True)
                final_selected.append(cluster[0]["job"])
                
        removed_count = initial_count - len(final_selected)
        return final_selected, removed_count

_global_deduplicator = MultiStageDeduplicator()

def deduplicate_jobs_multi_stage(jobs: List[Job]) -> Tuple[List[Job], int]:
    return _global_deduplicator.deduplicate(jobs)
