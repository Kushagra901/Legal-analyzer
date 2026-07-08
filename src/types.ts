/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export type DocumentStatus = 'processing' | 'completed' | 'flagged' | 'failed';
export type RiskLevel = 'low' | 'medium' | 'high';

export interface ExtractedClause {
  id: string;
  title: string;
  category: string;
  text: string;
  riskLevel: RiskLevel;
  explanation: string;
  suggestedAction: string;
  humanReviewed: boolean;
  flaggedForReview: boolean;
  highlightIndex?: number; // references a highlight block in the document text
}

export interface ReportMemo {
  id: string;
  title: string;
  date: string;
  author: string;
  executiveSummary: string;
  complianceScore: number; // 0 to 100 (high is better)
  recommendations: string[];
}

export interface LegalDocument {
  id: string;
  name: string;
  uploadDate: string;
  fileSize: string;
  status: DocumentStatus;
  riskLevel: RiskLevel;
  complianceScore: number;
  originalText: string;
  summary: string;
  clauses: ExtractedClause[];
  reportMemo: ReportMemo;
  reviewConfidence: number; // 0-100 confidence score
  reviewerNotes?: string;
}

export interface UserSession {
  name: string;
  role: string;
  email: string;
  isLoggedIn: boolean;
}
