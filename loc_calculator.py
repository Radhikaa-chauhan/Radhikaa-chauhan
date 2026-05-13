#!/usr/bin/env python3
"""
GitHub LoC (Lines of Code) Calculator
Calculates total lines of code across all repositories for a GitHub user
"""

import requests
import json
import sys
import argparse
from datetime import datetime
from collections import defaultdict
import os

class GitHubLoCCalculator:
    def __init__(self, username, token=None):
        self.username = username
        self.token = token
        self.headers = {
            'Accept': 'application/vnd.github.v3+json'
        }
        if token:
            self.headers['Authorization'] = f'token {token}'
        
        self.api_base = 'https://api.github.com'
        self.repositories = []
        self.total_loc = 0
        self.language_stats = defaultdict(int)
        self.repo_stats = []
        
    def get_user_repos(self):
        """Fetch all repositories for the user"""
        print(f"📦 Fetching repositories for user: {self.username}...")
        
        page = 1
        while True:
            url = f'{self.api_base}/users/{self.username}/repos'
            params = {
                'page': page,
                'per_page': 100,
                'type': 'all'
            }
            
            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                repos = response.json()
                
                if not repos:
                    break
                
                self.repositories.extend(repos)
                page += 1
                print(f"  ✓ Fetched page {page-1} ({len(repos)} repos)")
                
            except requests.exceptions.RequestException as e:
                print(f"  ✗ Error fetching repositories: {e}")
                break
        
        print(f"✓ Total repositories found: {len(self.repositories)}\n")
        return self.repositories
    
    def get_repo_languages(self, repo):
        """Get language statistics for a repository"""
        try:
            url = f"{self.api_base}/repos/{repo['full_name']}/languages"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"  ⚠ Error fetching languages for {repo['name']}: {e}")
            return {}
    
    def calculate_loc(self):
        """Calculate total lines of code across all repositories"""
        print("📊 Calculating Lines of Code...\n")
        
        total_repos = len(self.repositories)
        
        for idx, repo in enumerate(self.repositories, 1):
            repo_name = repo['name']
            print(f"[{idx}/{total_repos}] Processing: {repo_name}...", end=" ")
            
            if repo['private']:
                print("(private - skipped)")
                continue
            
            if repo['fork']:
                print("(fork - skipped)")
                continue
            
            try:
                languages = self.get_repo_languages(repo)
                
                if not languages:
                    print("(no code)")
                    continue
                
                repo_loc = sum(languages.values())
                self.total_loc += repo_loc
                
                # Track language statistics
                for language, bytes_count in languages.items():
                    self.language_stats[language] += bytes_count
                
                self.repo_stats.append({
                    'name': repo_name,
                    'full_name': repo['full_name'],
                    'url': repo['html_url'],
                    'loc': repo_loc,
                    'languages': languages,
                    'description': repo['description'] or 'N/A',
                    'stars': repo['stargazers_count'],
                    'forks': repo['forks_count'],
                    'created_at': repo['created_at'],
                    'updated_at': repo['updated_at']
                })
                
                print(f"✓ ({repo_loc} LoC)")
                
            except Exception as e:
                print(f"✗ Error: {e}")
                continue
        
        return self.total_loc
    
    def generate_report(self):
        """Generate a detailed report"""
        # Sort repositories by LoC
        sorted_repos = sorted(self.repo_stats, key=lambda x: x['loc'], reverse=True)
        
        # Sort languages by LoC
        sorted_languages = sorted(self.language_stats.items(), 
                                 key=lambda x: x[1], reverse=True)
        
        report = {
            'summary': {
                'username': self.username,
                'total_repositories_processed': len(self.repo_stats),
                'total_lines_of_code': self.total_loc,
                'generated_at': datetime.now().isoformat(),
                'average_loc_per_repo': self.total_loc // len(self.repo_stats) if self.repo_stats else 0
            },
            'top_repositories': sorted_repos[:10],
            'language_statistics': [
                {'language': lang, 'bytes': bytes_count, 
                 'percentage': round((bytes_count / sum(dict(self.language_stats).values()) * 100), 2)}
                for lang, bytes_count in sorted_languages
            ],
            'all_repositories': sorted_repos
        }
        
        return report
    
    def print_summary(self, report):
        """Print a formatted summary to console"""
        summary = report['summary']
        
        print("\n" + "="*70)
        print("📈 LINES OF CODE SUMMARY")
        print("="*70)
        print(f"\n👤 User: {summary['username']}")
        print(f"📦 Repositories Analyzed: {summary['total_repositories_processed']}")
        print(f"📊 Total Lines of Code: {summary['total_lines_of_code']:,}")
        print(f"📈 Average LoC per Repository: {summary['average_loc_per_repo']:,}")
        print(f"🕐 Generated: {summary['generated_at']}")
        
        print("\n" + "-"*70)
        print("🏆 TOP 10 REPOSITORIES BY LoC")
        print("-"*70)
        
        for idx, repo in enumerate(report['top_repositories'], 1):
            print(f"\n{idx}. {repo['name']}")
            print(f"   LoC: {repo['loc']:,}")
            print(f"   URL: {repo['url']}")
            print(f"   Primary Languages: {', '.join(list(repo['languages'].keys())[:3])}")
            print(f"   ⭐ Stars: {repo['stars']} | 🍴 Forks: {repo['forks']}")
        
        print("\n" + "-"*70)
        print("💻 LANGUAGE DISTRIBUTION")
        print("-"*70)
        
        for idx, (lang_info) in enumerate(report['language_statistics'][:15], 1):
            percentage_bar = "█" * int(lang_info['percentage'] / 5) + "░" * (20 - int(lang_info['percentage'] / 5))
            print(f"{idx:2}. {lang_info['language']:15} | {percentage_bar} {lang_info['percentage']:5.1f}%")
        
        print("\n" + "="*70)
    
    def save_json_report(self, report):
        """Save report to JSON file"""
        filename = f"loc-report-{self.username}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 JSON Report saved: {filename}")
        return filename
    
    def run(self):
        """Run the complete calculation"""
        print("\n🚀 Starting GitHub LoC Calculator\n")
        
        try:
            self.get_user_repos()
            
            if not self.repositories:
                print("❌ No repositories found!")
                return
            
            self.calculate_loc()
            report = self.generate_report()
            
            self.print_summary(report)
            self.save_json_report(report)
            
            print("\n✅ Calculation complete!\n")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

def main():
    parser = argparse.ArgumentParser(
        description='Calculate Lines of Code across GitHub repositories',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python3 loc_calculator.py Radhikaa-chauhan
  python3 loc_calculator.py Radhikaa-chauhan --token ghp_xxxxxxxxxxxx
        '''
    )
    
    parser.add_argument('username', help='GitHub username')
    parser.add_argument('--token', help='GitHub personal access token (optional, for higher rate limits)')
    
    args = parser.parse_args()
    
    calculator = GitHubLoCCalculator(args.username, args.token)
    calculator.run()

if __name__ == '__main__':
    main()
