"""Service layer for feedback analysis and file processing."""

import io
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import UploadFile

from ...core.logging import get_logger
from ...infra.storage import storage
from ..chains.feedback_chain import FeedbackChain
from ..models.feedback import FeedbackAnalyzeResponse

logger = get_logger(__name__)


class FeedbackService:
    """Service for orchestrating feedback analysis and file processing."""

    def __init__(self) -> None:
        """Initialize the feedback service."""
        self.chain = FeedbackChain()

    async def analyze_file(self, file: UploadFile) -> FeedbackAnalyzeResponse:
        """Analyze feedback from uploaded CSV/XLSX file."""
        
        logger.info(f"📄 Starting feedback analysis for file: {file.filename}")
        
        try:
            # Read and parse file
            comments_data = await self._parse_feedback_file(file)
            
            if not comments_data:
                raise ValueError("No valid comments found in file")

            logger.info(f"📊 Parsed {len(comments_data)} comments from file")

            # Analyze comments using chain
            analyses = await self.chain.analyze_batch(comments_data)
            
            # Aggregate results
            result = self.chain.aggregate_results(analyses, comments_data)
            
            # Save results for potential export
            job_id = await self._save_analysis_results(file.filename or "feedback.xlsx", result, comments_data)
            
            logger.info(f"✅ Feedback analysis complete: {job_id}")
            return result

        except Exception as e:
            logger.error(f"💥 Feedback analysis failed: {e}")
            raise

    async def _parse_feedback_file(self, file: UploadFile) -> List[Dict[str, Any]]:
        """Parse CSV or XLSX file and extract comment data."""
        
        try:
            # Read file content
            content = await file.read()
            file_extension = Path(file.filename or "").suffix.lower()
            
            logger.info(f"📝 Parsing {file_extension} file ({len(content)} bytes)")

            # Parse based on file type
            if file_extension == '.csv':
                df = pd.read_csv(io.BytesIO(content))
            elif file_extension in ['.xlsx', '.xls']:
                df = pd.read_excel(io.BytesIO(content))
            else:
                raise ValueError(f"Unsupported file format: {file_extension}. Use CSV or XLSX.")

            logger.info(f"📋 File loaded: {len(df)} rows, {len(df.columns)} columns")

            # Validate required columns
            required_columns = ['comment']
            optional_columns = ['username', 'channel', 'date']
            
            missing_required = [col for col in required_columns if col not in df.columns]
            if missing_required:
                # Try common variations
                column_mapping = {
                    'comment': ['comment', 'comentario', 'feedback', 'review', 'opinion', 'text'],
                    'username': ['username', 'user', 'usuario', 'name', 'nombre'],
                    'channel': ['channel', 'canal', 'platform', 'plataforma', 'source'],
                    'date': ['date', 'fecha', 'timestamp', 'created_at']
                }
                
                # Try to map columns
                for standard_col, variations in column_mapping.items():
                    for variation in variations:
                        if variation in df.columns:
                            df = df.rename(columns={variation: standard_col})
                            break

                # Check again for required columns
                missing_required = [col for col in required_columns if col not in df.columns]
                if missing_required:
                    available_columns = list(df.columns)
                    raise ValueError(
                        f"Missing required columns: {missing_required}. "
                        f"Available columns: {available_columns}. "
                        f"Required: comment column with feedback text."
                    )

            # Clean and prepare data
            df = df.dropna(subset=['comment'])  # Remove rows without comments
            df['comment'] = df['comment'].astype(str).str.strip()
            df = df[df['comment'].str.len() > 5]  # Remove very short comments

            # Add default values for optional columns
            for col in optional_columns:
                if col not in df.columns:
                    if col == 'username':
                        df[col] = 'anonymous'
                    else:
                        df[col] = None

            # Convert to list of dicts
            comments_data = df.to_dict('records')
            
            # Filter valid comments
            valid_comments = []
            for comment_data in comments_data:
                comment = str(comment_data.get('comment', '')).strip()
                if len(comment) > 5 and len(comment) < 1000:  # Reasonable length
                    valid_comments.append({
                        'comment': comment,
                        'username': str(comment_data.get('username', 'anonymous')),
                        'channel': comment_data.get('channel'),
                        'date': comment_data.get('date')
                    })

            logger.info(f"✅ Parsed {len(valid_comments)} valid comments (filtered from {len(comments_data)})")
            return valid_comments

        except Exception as e:
            logger.error(f"❌ File parsing failed: {e}")
            raise

    async def _save_analysis_results(
        self, 
        filename: str, 
        result: FeedbackAnalyzeResponse,
        comments_data: List[Dict[str, Any]]
    ) -> str:
        """Save analysis results for potential export."""
        
        try:
            job_id = storage.create_job_directory()
            
            # Save main results
            results_data = {
                "analysis": result.model_dump(),
                "input_file": filename,
                "total_comments": len(comments_data),
                "processing_summary": {
                    "overall_sentiment": result.overall_sentiment.model_dump(),
                    "themes_count": len(result.themes),
                    "issues_count": len(result.top_issues),
                    "feature_requests_count": len(result.feature_requests),
                    "highlights_count": len(result.highlights)
                }
            }
            
            storage.save_metadata(job_id, results_data, "analysis_results.json")
            
            # Save detailed data for export
            export_data = {
                "comments_data": comments_data,
                "analysis_results": result.model_dump()
            }
            
            storage.save_metadata(job_id, export_data, "export_data.json")
            
            logger.info(f"💾 Analysis results saved: {job_id}")
            return job_id

        except Exception as e:
            logger.error(f"❌ Failed to save analysis results: {e}")
            return "error"

    async def export_results_to_excel(self, job_id: str) -> Optional[str]:
        """Export analysis results to Excel file with multiple sheets."""
        
        try:
            # Load export data
            export_data = storage.load_metadata(job_id, "export_data.json")
            if not export_data:
                return None

            comments_data = export_data["comments_data"]
            analysis_results = export_data["analysis_results"]
            
            # Create Excel file with multiple sheets
            excel_path = storage.artifacts_path / job_id / "feedback_analysis.xlsx"
            
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                
                # Sheet 1: Summary
                summary_data = {
                    'Metric': ['Total Comments', 'Overall Sentiment', 'Sentiment Score', 'Themes Found', 'Issues Found', 'Feature Requests'],
                    'Value': [
                        len(comments_data),
                        analysis_results['overall_sentiment']['label'],
                        f"{analysis_results['overall_sentiment']['score']:.2f}",
                        len(analysis_results['themes']),
                        len(analysis_results['top_issues']),
                        len(analysis_results['feature_requests'])
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                
                # Sheet 2: Themes
                if analysis_results['themes']:
                    themes_data = []
                    for theme in analysis_results['themes']:
                        themes_data.append({
                            'Theme': theme['name'],
                            'Examples': '; '.join(theme['examples'][:2])  # First 2 examples
                        })
                    pd.DataFrame(themes_data).to_excel(writer, sheet_name='Themes', index=False)
                
                # Sheet 3: Issues
                if analysis_results['top_issues']:
                    issues_data = []
                    for issue in analysis_results['top_issues']:
                        issues_data.append({
                            'Issue': issue['issue'],
                            'Count': issue['count'],
                            'Priority': issue['priority']
                        })
                    pd.DataFrame(issues_data).to_excel(writer, sheet_name='Issues', index=False)
                
                # Sheet 4: Feature Requests
                if analysis_results['feature_requests']:
                    requests_data = []
                    for request in analysis_results['feature_requests']:
                        requests_data.append({
                            'Feature Request': request['request'],
                            'Count': request['count']
                        })
                    pd.DataFrame(requests_data).to_excel(writer, sheet_name='Feature Requests', index=False)
                
                # Sheet 5: Highlights
                if analysis_results['highlights']:
                    highlights_data = []
                    for highlight in analysis_results['highlights']:
                        highlights_data.append({
                            'Quote': highlight['quote'],
                            'SKU': highlight.get('sku', 'N/A'),
                            'Channel': highlight.get('channel', 'N/A')
                        })
                    pd.DataFrame(highlights_data).to_excel(writer, sheet_name='Highlights', index=False)
                
                # Sheet 6: By SKU (if available)
                if analysis_results['by_sku']:
                    sku_data = []
                    for sku, data in analysis_results['by_sku'].items():
                        sku_data.append({
                            'SKU': sku,
                            'Total Comments': data['total_comments'],
                            'Positive': data['sentiment_distribution'].get('positive', 0),
                            'Neutral': data['sentiment_distribution'].get('neutral', 0),
                            'Negative': data['sentiment_distribution'].get('negative', 0),
                            'Top Themes': ', '.join(data['top_themes'][:3])
                        })
                    pd.DataFrame(sku_data).to_excel(writer, sheet_name='By SKU', index=False)
                
                # Sheet 7: By Channel (if available)
                if analysis_results['by_channel']:
                    channel_data = []
                    for channel, data in analysis_results['by_channel'].items():
                        channel_data.append({
                            'Channel': channel,
                            'Total Comments': data['total_comments'],
                            'Positive': data['sentiment_distribution'].get('positive', 0),
                            'Neutral': data['sentiment_distribution'].get('neutral', 0),
                            'Negative': data['sentiment_distribution'].get('negative', 0),
                            'Top Themes': ', '.join(data['top_themes'][:3])
                        })
                    pd.DataFrame(channel_data).to_excel(writer, sheet_name='By Channel', index=False)

            logger.info(f"📊 Excel export created: feedback_analysis.xlsx")
            return str(excel_path)

        except Exception as e:
            logger.error(f"❌ Excel export failed: {e}")
            return None

    def get_analysis_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a completed analysis."""
        
        try:
            results_data = storage.load_metadata(job_id, "analysis_results.json")
            if not results_data:
                return None

            artifacts = storage.list_job_artifacts(job_id)
            
            return {
                "job_id": job_id,
                "input_file": results_data.get("input_file", "unknown"),
                "total_comments": results_data.get("total_comments", 0),
                "processing_summary": results_data.get("processing_summary", {}),
                "artifacts": artifacts,
                "has_excel_export": "feedback_analysis.xlsx" in artifacts
            }

        except Exception as e:
            logger.error(f"❌ Failed to get analysis info for {job_id}: {e}")
            return None