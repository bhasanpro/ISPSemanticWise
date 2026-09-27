"""
Jira/Confluence Connector - Extracts issues, comments, and documentation
"""

from typing import Dict, List, Any, Optional
from loguru import logger
from atlassian import Jira, Confluence

from .base import BaseIngestionConnector, IngestionResult


class JiraConnector(BaseIngestionConnector):
    """Connector for Jira issues and Confluence pages"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.enabled = config.get("enabled", False)
        self.jira_url = config.get("jira_url", "")
        self.jira_user = config.get("jira_user", "")
        self.jira_token = config.get("jira_api_token", "")
        self.project_key = config.get("jira_project_key", "PTM")
        self.issue_types = config.get("issue_types", ["Bug", "Story", "Task", "Incident"])
        
        self.jira = None
        self.confluence = None
        
        if self.enabled and self.jira_url and self.jira_user and self.jira_token:
            self._init_clients()
    
    def _init_clients(self):
        """Initialize Jira and Confluence clients"""
        try:
            self.jira = Jira(
                url=self.jira_url,
                username=self.jira_user,
                password=self.jira_token,
                cloud=True,
            )
            
            confluence_url = self.jira_url.replace("jira", "wiki") if "jira" in self.jira_url else self.jira_url
            self.confluence = Confluence(
                url=confluence_url,
                username=self.jira_user,
                password=self.jira_token,
                cloud=True,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Atlassian clients: {e}")
    
    def discover(self) -> List[str]:
        """Discover Jira issues"""
        if not self.enabled or not self.jira:
            return []
        
        try:
            jql = f"project = {self.project_key} AND issuetype IN ({','.join(self.issue_types)}) ORDER BY updated DESC"
            issues = self.jira.jql(jql, limit=1000)
            return [issue['key'] for issue in issues.get('issues', [])]
        except Exception as e:
            logger.error(f"Failed to discover Jira issues: {e}")
            return []
    
    def extract(self, source: str) -> List[Dict[str, Any]]:
        """Extract Jira issue details"""
        if not self.jira:
            return []
        
        issue_key = source
        
        try:
            issue = self.jira.issue(issue_key, expand='comments,changelog')
            
            return [{
                "artifact_type": "jira_issue",
                "name": issue_key,
                "source_system": "jira",
                "path": f"jira/{issue_key}",
                "code_snippet": "",
                "metadata": {
                    "issue_key": issue_key,
                    "summary": issue['fields']['summary'],
                    "description": issue['fields'].get('description', ''),
                    "status": issue['fields']['status']['name'],
                    "issue_type": issue['fields']['issuetype']['name'],
                    "priority": issue['fields']['priority']['name'] if issue['fields'].get('priority') else None,
                    "assignee": issue['fields']['assignee']['displayName'] if issue['fields'].get('assignee') else None,
                    "reporter": issue['fields']['reporter']['displayName'] if issue['fields'].get('reporter') else None,
                    "created": issue['fields']['created'],
                    "updated": issue['fields']['updated'],
                    "labels": issue['fields'].get('labels', []),
                    "components": [c['name'] for c in issue['fields'].get('components', [])],
                    "comments": self._extract_comments(issue),
                    "changelog": self._extract_changelog(issue),
                },
            }]
        except Exception as e:
            logger.error(f"Failed to extract Jira issue {issue_key}: {e}")
            return []
    
    def _extract_comments(self, issue) -> List[Dict]:
        """Extract comments from issue"""
        comments = []
        for comment in issue['fields']['comment']['comments']:
            comments.append({
                "author": comment['author']['displayName'],
                "body": comment['body'],
                "created": comment['created'],
                "updated": comment['updated'],
            })
        return comments
    
    def _extract_changelog(self, issue) -> List[Dict]:
        """Extract changelog from issue"""
        changes = []
        for history in issue.get('changelog', {}).get('histories', []):
            for item in history['items']:
                changes.append({
                    "field": item['field'],
                    "from": item['fromString'],
                    "to": item['toString'],
                    "author": history['author']['displayName'],
                    "created": history['created'],
                })
        return changes
    
    def transform(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform Jira issues to standard artifacts"""
        transformed = []
        
        for item in raw_data:
            meta = item["metadata"]
            
            # Main issue artifact
            transformed.append({
                "artifact_type": "jira_issue",
                "name": meta["issue_key"],
                "source_system": "jira",
                "path": f"jira/{meta['issue_key']}",
                "code_snippet": meta["description"] or "",
                "metadata": {
                    **meta,
                    "artifact_category": "issue",
                },
            })
            
            # Comments as separate artifacts
            for i, comment in enumerate(meta.get("comments", [])):
                transformed.append({
                    "artifact_type": "jira_comment",
                    "name": f"{meta['issue_key']}_comment_{i}",
                    "source_system": "jira",
                    "path": f"jira/{meta['issue_key']}/comment_{i}",
                    "code_snippet": comment["body"],
                    "metadata": {
                        "issue_key": meta["issue_key"],
                        "author": comment["author"],
                        "created": comment["created"],
                    },
                })
            
            # Changelog entries
            for change in meta.get("changelog", []):
                transformed.append({
                    "artifact_type": "jira_change",
                    "name": f"{meta['issue_key']}_change_{change['field']}",
                    "source_system": "jira",
                    "path": f"jira/{meta['issue_key']}/change_{change['field']}",
                    "code_snippet": f"{change['field']}: {change['from']} -> {change['to']}",
                    "metadata": {
                        "issue_key": meta["issue_key"],
                        "field": change["field"],
                        "from": change["from"],
                        "to": change["to"],
                        "author": change["author"],
                        "created": change["created"],
                    },
                })
        
        return transformed
    
    def load(self, transformed_data: List[Dict[str, Any]]) -> IngestionResult:
        """Load to storage"""
        return IngestionResult(
            job_id=self.job.job_id if self.job else "",
            success=True,
            items=transformed_data,
        )