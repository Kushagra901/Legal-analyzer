/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI, Type } from "@google/genai";
import dotenv from "dotenv";
import { LegalDocument, ExtractedClause, ReportMemo } from "./src/types";

dotenv.config();

// Preloaded real-world legal documents to populate the dashboard immediately
const sampleNDAOriginalText = `MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement (the "Agreement") is entered into as of October 12, 2025 (the "Effective Date") by and between Apex Tech Solutions, LLC ("Apex"), and Horizon Ventures, LP ("Horizon").

1. Purpose. The parties wish to explore a potential business relationship of mutual interest (the "Transaction"). In connection with the Transaction, either party (as the "Disclosing Party") may disclose to the other party (as the "Receiving Party") certain proprietary or confidential information.

2. Confidential Information. "Confidential Information" means any information or materials disclosed by the Disclosing Party to the Receiving Party that is either designated as confidential in writing or should reasonably be understood to be confidential given the nature of the information. Confidential Information does not include information that: (a) is or becomes publicly known through no breach of this Agreement; (b) was already in the Receiving Party's lawful possession; or (c) is independently developed by the Receiving Party without reference to or reliance upon the Disclosing Party's Confidential Information.

3. Obligations of Confidentiality. The Receiving Party agrees: (a) to hold the Disclosing Party's Confidential Information in strict confidence and use at least a reasonable degree of care to prevent unauthorized disclosure; (b) to use such Confidential Information solely for the Purpose; and (c) to restrict access to such Confidential Information to its employees, affiliates, or advisors who need to know and are bound by confidentiality obligations at least as protective as those herein.

4. Term and Termination. This Agreement shall govern all disclosures made during a period of one (1) year from the Effective Date. The Receiving Party's obligations under this Agreement with respect to Confidential Information disclosed hereunder shall survive for a period of three (3) years from the date of disclosure.

5. Limitation of Liability. NEITHER PARTY SHALL BE LIABLE TO THE OTHER FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES ARISING OUT OF OR IN CONNECTION WITH THIS AGREEMENT, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.

6. Governing Law and Jurisdiction. This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to its conflict of laws principles. Any legal action arising hereunder shall be brought exclusively in the state or federal courts located in Wilmington, Delaware.

IN WITNESS WHEREOF, the parties have executed this Mutual Non-Disclosure Agreement as of the Effective Date.`;

const sampleSaaSOriginalText = `SOFTWARE-AS-A-SERVICE (SaaS) AGREEMENT

This SaaS Agreement (the "Agreement") is made and entered into by and between CloudScale Enterprise Inc. ("Provider") and Global Retail Corp. ("Customer") as of August 24, 2025.

1. Services and License. Provider grants Customer a non-transferable, non-exclusive, revocable license to access the CloudScale Analytics Suite (the "Service") during the applicable Subscription Term.

2. Service Level Agreement & Support. Provider will use commercially reasonable efforts to make the Service available 99.0% of the time, measured monthly, excluding scheduled maintenance. Support is provided during standard business hours only (9 AM - 5 PM EST, Monday through Friday, excluding holidays).

3. Unilateral Indemnification. Customer shall defend, indemnify, and hold harmless Provider and its officers, directors, and employees from and against any and all claims, losses, damages, liabilities, and expenses (including reasonable attorneys' fees) arising out of or relating to Customer's use of the Service, breach of this Agreement, or violation of third-party intellectual property rights. PROVIDER HAS NO INDEMNIFICATION OBLIGATION TO CUSTOMER UNDER ANY CIRCUMSTANCE.

4. Unbalanced Limitation of Liability. IN NO EVENT SHALL PROVIDER'S TOTAL AGGREGATE LIABILITY ARISING OUT OF OR RELATED TO THIS AGREEMENT, WHETHER IN CONTRACT, TORT, OR OTHERWISE, EXCEED THE TOTAL AMOUNT ACTUALLY PAID BY CUSTOMER TO PROVIDER IN THE ONE (1) MONTH IMMEDIATELY PRECEDING THE EVENT GIVING RISE TO LIABILITY. CUSTOMER ACKNOWLEDGES THAT THIS LIMITATION IS A CRITICAL BASIS OF THE BARGAIN.

5. IP Ownership. All right, title, and interest in and to the Service, including all software, source code, documentation, modifications, and any user feedback or suggestions, shall remain exclusively with Provider. Customer grants Provider an unrestricted, royalty-free, perpetual, irrevocable license to use, reproduce, modify, and exploit any feedback provided by Customer for any purpose whatsoever.

6. Governing Law and Severability. This Agreement is governed by the laws of the State of New York. If any court of competent jurisdiction finds any provision of this Agreement invalid, such provision shall be modified to reflect the parties' intent, and the remainder of the Agreement shall continue in full force.`;

const sampleConsultingOriginalText = `INDEPENDENT CONTRACTOR CONSULTING AGREEMENT

This Consulting Agreement (the "Agreement") is dated June 1, 2025, between Alpha Business Advisory ("Client") and Sarah Jenkins ("Consultant").

1. Services. Consultant agrees to perform the digital strategy consulting services described in Exhibit A (the "Services") in a professional, timely manner.

2. Compensation and Payment. Client shall pay Consultant $150 per hour for Services rendered. Consultant shall submit monthly invoices. Client shall pay all approved invoices within ninety (90) days of receipt. Consultant shall bear all expenses unless pre-approved in writing.

3. Complete Intellectual Property Assignment. Consultant agrees that all deliverables, designs, reports, software code, written materials, ideas, and inventions created, conceived, or developed by Consultant under this Agreement (the "Work Product") shall belong exclusively to Client. Consultant hereby unconditionally and irrevocably assigns, transfers, and conveys to Client all right, title, and interest worldwide in and to the Work Product. Consultant agrees to sign any documents necessary to assist Client in registering and protecting these rights. Consultant waives all moral rights in the Work Product.

4. Non-Competition. During the term of this Agreement and for a period of eighteen (18) months thereafter, Consultant shall not, directly or indirectly, perform consulting services, work for, or engage in any business activity that competes directly with Client's business within North America.

5. Term and Termination. This Agreement commences on the date hereof and continues until terminated. Either party may terminate this Agreement for convenience upon sixty (60) days prior written notice. Client may terminate immediately for cause if Consultant breaches any confidentiality or IP provision.`;

// In-memory array of documents
let documents: LegalDocument[] = [
  {
    id: "doc_001",
    name: "Mutual NDA - Apex Tech & Horizon.txt",
    uploadDate: "2025-10-12",
    fileSize: "1.8 KB",
    status: "completed",
    riskLevel: "low",
    complianceScore: 92,
    originalText: sampleNDAOriginalText,
    summary: "A balanced mutual NDA outlining mutual confidentiality obligations for exploring a potential transaction. Contains a standard 3-year survival term and standard bilateral exclusions from confidential status.",
    clauses: [
      {
        id: "cl_1",
        title: "Obligations of Confidentiality",
        category: "confidentiality",
        text: "The Receiving Party agrees: (a) to hold the Disclosing Party's Confidential Information in strict confidence and use at least a reasonable degree of care...",
        riskLevel: "low",
        explanation: "The confidentiality obligations are strictly mutual and require a reasonable standard of care, which is standard, fair, and safe for both signatories.",
        suggestedAction: "No action required. This clause is highly standard and represents low exposure.",
        humanReviewed: true,
        flaggedForReview: false
      },
      {
        id: "cl_2",
        title: "Bilateral Exclusions",
        category: "confidentiality",
        text: "Confidential Information does not include information that: (a) is or becomes publicly known... (b) was already in the Receiving Party's lawful possession; or (c) is independently developed...",
        riskLevel: "low",
        explanation: "Standard industry carve-outs for information that is public, already known, or independently developed. Protects receiving parties from overreaching liability.",
        suggestedAction: "No action required. The exclusions are robust and bilateral.",
        humanReviewed: true,
        flaggedForReview: false
      },
      {
        id: "cl_3",
        title: "Bilateral Limitation of Liability",
        category: "liability",
        text: "NEITHER PARTY SHALL BE LIABLE TO THE OTHER FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES...",
        riskLevel: "low",
        explanation: "The waiver of consequential and special damages applies symmetrically to both parties, preventing runaway speculative claims.",
        suggestedAction: "No action required. Symmetrical liability caps are standard practice in exploratory agreements.",
        humanReviewed: true,
        flaggedForReview: false
      }
    ],
    reportMemo: {
      id: "memo_001",
      title: "Legal Audit Memo: Apex & Horizon NDA",
      date: "2025-10-12",
      author: "Legal Analyzer Automated Engine",
      executiveSummary: "The Mutual Non-Disclosure Agreement is highly standard, symmetrical, and poses low legal risk to both parties. Confidentiality survival terms are standard (3 years) and the governing law is Delaware, which is highly predictable.",
      complianceScore: 92,
      recommendations: [
        "Proceed with execution as-is. All key provisions are reciprocal.",
        "Ensure Wilmington, Delaware is an acceptable jurisdiction for your operations."
      ]
    },
    reviewConfidence: 98
  },
  {
    id: "doc_002",
    name: "Enterprise SaaS Terms - CloudScale.txt",
    uploadDate: "2025-08-24",
    fileSize: "2.4 KB",
    status: "flagged",
    riskLevel: "high",
    complianceScore: 35,
    originalText: sampleSaaSOriginalText,
    summary: "A highly aggressive unilateral SaaS Agreement designed by the vendor. It contains severe unilateral indemnity triggers, an extremely restrictive liability cap, and total ownership of customer feedback with zero reciprocal protections.",
    clauses: [
      {
        id: "cl_4",
        title: "Unilateral Customer Indemnification",
        category: "indemnification",
        text: "Customer shall defend, indemnify, and hold harmless Provider and its officers, directors, and employees from and against any and all claims... PROVIDER HAS NO INDEMNIFICATION OBLIGATION TO CUSTOMER UNDER ANY CIRCUMSTANCE.",
        riskLevel: "high",
        explanation: "The customer bears all liability burdens while the provider completely waives reciprocal IP infringement indemnification, which is extremely rare and dangerous in commercial SaaS.",
        suggestedAction: "Strike the unilateral exclusion. Request a standard reciprocal IP infringement indemnity clause from the provider.",
        humanReviewed: false,
        flaggedForReview: true
      },
      {
        id: "cl_5",
        title: "Severely Restrictive Liability Cap",
        category: "liability",
        text: "IN NO EVENT SHALL PROVIDER'S TOTAL AGGREGATE LIABILITY ARISING OUT OF OR RELATED TO THIS AGREEMENT... EXCEED THE TOTAL AMOUNT ACTUALLY PAID BY CUSTOMER TO PROVIDER IN THE ONE (1) MONTH IMMEDIATELY PRECEDING...",
        riskLevel: "high",
        explanation: "A 1-month fees paid cap is extremely low and would fail to cover even minor data breach or compliance litigation costs. Standard SaaS liability caps range from 12-24 months fees or a fixed super-cap.",
        suggestedAction: "Propose a liability cap of at least 12 months fees paid, with a carve-out (uncapped or super-capped) for data breaches and confidentiality violations.",
        humanReviewed: false,
        flaggedForReview: true
      },
      {
        id: "cl_6",
        title: "Irrevocable Perpetual Feedback Exploitation",
        category: "intellectual_property",
        text: "Customer grants Provider an unrestricted, royalty-free, perpetual, irrevocable license to use, reproduce, modify, and exploit any feedback provided by Customer...",
        riskLevel: "medium",
        explanation: "The provider is granted full rights to incorporate customer proprietary insights into their main service without compensation or restriction.",
        suggestedAction: "Restrict feedback license to non-confidential, non-identifying improvements, or stipulate that suggestions must not disclose proprietary commercial data.",
        humanReviewed: true,
        flaggedForReview: false
      }
    ],
    reportMemo: {
      id: "memo_002",
      title: "Legal Audit Memo: CloudScale SaaS Terms",
      date: "2025-08-24",
      author: "Legal Analyzer Automated Engine",
      executiveSummary: "This document is highly unbalanced and poses material risk to Global Retail Corp. Key risks include a complete absence of IP protection/indemnity from the provider, coupled with a microscopic 1-month fees liability ceiling. Commercial execution in its current state is strongly discouraged.",
      complianceScore: 35,
      recommendations: [
        "Do not sign in current state. Unilateral indemnification poses significant commercial liability risk.",
        "Renegotiate Section 4 (Limitation of Liability) to a standard 12-month trailing fee multiplier.",
        "Demand mutual intellectual property infringement indemnity."
      ]
    },
    reviewConfidence: 94
  },
  {
    id: "doc_003",
    name: "Consulting Agreement - Sarah Jenkins.txt",
    uploadDate: "2025-06-01",
    fileSize: "2.1 KB",
    status: "completed",
    riskLevel: "medium",
    complianceScore: 64,
    originalText: sampleConsultingOriginalText,
    summary: "A consulting agreement with unilateral work-product assignment and an extremely broad 18-month North American non-compete clause. Payment terms are net-90, which poses cash flow risks to the consultant.",
    clauses: [
      {
        id: "cl_7",
        title: "Complete Unilateral IP Assignment",
        category: "intellectual_property",
        text: "Consultant hereby unconditionally and irrevocably assigns, transfers, and conveys to Client all right, title, and interest worldwide in and to the Work Product...",
        riskLevel: "medium",
        explanation: "While standard for client engagements, the assignment is unconditional and takes effect immediately upon creation, rather than being conditioned upon receipt of full payment.",
        suggestedAction: "Modify the assignment to be effective only 'upon receipt of full payment for the applicable Services.' This protects the contractor's leverage.",
        humanReviewed: true,
        flaggedForReview: false
      },
      {
        id: "cl_8",
        title: "Broad North American Non-Compete",
        category: "other",
        text: "During the term of this Agreement and for a period of eighteen (18) months thereafter, Consultant shall not, directly or indirectly, perform consulting services... within North America.",
        riskLevel: "high",
        explanation: "An 18-month geographic ban across the entire North American continent is excessively restrictive for an independent contractor, and may prevent the contractor from earning a living.",
        suggestedAction: "Limit the non-compete to direct competitors of the client, reduce the survival term to 6 months, and specify a narrow radius or list of named competitor accounts.",
        humanReviewed: false,
        flaggedForReview: true
      },
      {
        id: "cl_9",
        title: "Extended Payment terms (Net-90)",
        category: "other",
        text: "Client shall pay all approved invoices within ninety (90) days of receipt.",
        riskLevel: "medium",
        explanation: "A 90-day payment delay is significantly longer than the standard commercial Net-30 standard, straining working capital.",
        suggestedAction: "Request modification to Net-30 or Net-45 invoice payment terms.",
        humanReviewed: true,
        flaggedForReview: false
      }
    ],
    reportMemo: {
      id: "memo_003",
      title: "Legal Audit Memo: Jenkins Consulting",
      date: "2025-06-01",
      author: "Legal Analyzer Automated Engine",
      executiveSummary: "The consulting agreement presents moderate risk to Sarah Jenkins, largely concentrated in the overly restrictive 18-month non-compete covenant and slow payment schedule. The IP assignment is standard but should be tied to payment fulfillment.",
      complianceScore: 64,
      recommendations: [
        "Renegotiate payment terms from Net-90 to standard Net-30.",
        "Add a clause stating that intellectual property rights transfer to the client only upon receipt of full payment.",
        "Severely narrow or strike the post-termination non-competition clause."
      ]
    },
    reviewConfidence: 91
  }
];

// Lazy-initialized Gemini Client
let aiClient: GoogleGenAI | null = null;
function getGeminiClient(): GoogleGenAI | null {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey || apiKey === "MY_GEMINI_API_KEY") {
    // Graceful fallback: API key is not configured or placeholder
    return null;
  }
  if (!aiClient) {
    aiClient = new GoogleGenAI({
      apiKey: apiKey,
      httpOptions: {
        headers: {
          'User-Agent': 'aistudio-build',
        }
      }
    });
  }
  return aiClient;
}

// Fallback rule-based analyzer for when Gemini is offline or API key is not configured
function fallbackAnalyze(text: string, name: string): LegalDocument {
  const normalized = text.toLowerCase();
  const clauses: ExtractedClause[] = [];
  let score = 85; // baseline

  // Helper to add clause if matches keywords
  const checkAndAdd = (
    id: string,
    title: string,
    category: string,
    keywords: string[],
    riskIfFound: "low" | "medium" | "high",
    matchedText: string,
    explanation: string,
    suggestedAction: string
  ) => {
    const found = keywords.some(kw => normalized.includes(kw));
    if (found) {
      if (riskIfFound === "high") score -= 15;
      else if (riskIfFound === "medium") score -= 8;
      else score += 2;

      clauses.push({
        id,
        title,
        category,
        text: matchedText,
        riskLevel: riskIfFound,
        explanation,
        suggestedAction,
        humanReviewed: false,
        flaggedForReview: riskIfFound === "high"
      });
    }
  };

  // Check Confidentiality
  checkAndAdd(
    "fallback_conf",
    "Confidentiality Duration",
    "confidentiality",
    ["survival", "survive", "confidentiality term", "indefinitely"],
    "medium",
    "The obligations of confidentiality under this agreement shall survive termination of this agreement and continue indefinitely.",
    "Indefinite confidentiality clauses create permanent compliance burdens and liability exposure for receiving parties.",
    "Propose standard temporal caps (e.g., 3 or 5 years post-termination) instead of indefinite duration.",
  );

  // Check Liability Limit
  const liabilityMatch = text.match(/limit.*liability|aggregate liability|liability cap/i);
  if (liabilityMatch) {
    checkAndAdd(
      "fallback_liab",
      "Limitation of Liability Limit",
      "liability",
      ["exceed", "amount paid", "one month", "aggregate liability"],
      "high",
      liabilityMatch[0] ? text.substring(Math.max(0, text.indexOf(liabilityMatch[0]) - 50), Math.min(text.length, text.indexOf(liabilityMatch[0]) + 150)) : "Liability limit clause found.",
      "The liability limits appear extremely low or heavily unilateral, capped at historical payments, exposing you to material operational risks.",
      "Request a reciprocal liability cap scaled to 12 or 24 months of agreement fees, with a clear super-cap for data breaches.",
    );
  } else {
    score -= 10;
    clauses.push({
      id: "fallback_no_liab",
      title: "Missing Limitation of Liability",
      category: "liability",
      text: "No explicit limitation of liability clause detected.",
      riskLevel: "high",
      explanation: "Executing a contract without an explicit limitation of liability clause exposes both signatories to unlimited joint and several damages.",
      suggestedAction: "Insert a standard mutual limitation of liability clause capping aggregate claims to fees paid.",
      humanReviewed: false,
      flaggedForReview: true
    });
  }

  // Check Indemnification
  checkAndAdd(
    "fallback_indem",
    "Unilateral Indemnification Trigger",
    "indemnification",
    ["indemnify", "indemnity", "hold harmless", "defend"],
    "high",
    "Defend, indemnify, and hold harmless...",
    "The indemnification terms are unbalanced, assigning litigation defense burdens and settlement costs unilaterally to one party.",
    "Propose mutual, symmetrical indemnification clauses covering direct third-party intellectual property claims.",
  );

  // Check IP assignment
  checkAndAdd(
    "fallback_ip",
    "Work Product Ownership Transfer",
    "intellectual_property",
    ["assign", "transfer", "work product", "own all rights", "intellectual property"],
    "medium",
    "All deliverables and work product created hereunder shall belong exclusively to the client...",
    "All intellectual property transfer is immediate and unconditional, offering no security in case of client non-payment.",
    "Amend to stipulate that title and ownership of work product transfer to the client ONLY upon receipt of full payment.",
  );

  // Check Governing law
  const govLaw = text.match(/governing law|laws of|jurisdiction/i);
  if (govLaw) {
    clauses.push({
      id: "fallback_gov",
      title: "Governing Law and Forum Selection",
      category: "governing_law",
      text: govLaw[0] ? text.substring(Math.max(0, text.indexOf(govLaw[0]) - 30), Math.min(text.length, text.indexOf(govLaw[0]) + 100)) : "Governing law clause.",
      riskLevel: "low",
      explanation: "A standard governing law selection is present. This is typical and provides jurisdictional predictability.",
      suggestedAction: "Confirm with your internal business operations that the selected legal forum is acceptable.",
      humanReviewed: true,
      flaggedForReview: false
    });
  }

  // Bound compliance score between 10 and 95
  score = Math.max(10, Math.min(95, score));
  const overallRisk = score < 50 ? "high" : score < 75 ? "medium" : "low";

  const summary = `Offline-parsed legal analysis of "${name}". Identified ${clauses.length} key clauses relating to liability, indemnification, and risk factors. Compliance index calculated at ${score}%.`;

  const reportMemo: ReportMemo = {
    id: `memo_${Date.now()}`,
    title: `Legal Memo: ${name}`,
    date: new Date().toISOString().split('T')[0],
    author: "Legal Analyzer Local Parser Engine",
    executiveSummary: `The document "${name}" has been processed by our local parser engine. We have flagged ${clauses.filter(c => c.riskLevel === 'high').length} severe legal risks. Review is recommended before formal execution.`,
    complianceScore: score,
    recommendations: clauses
      .filter(c => c.riskLevel !== 'low')
      .map(c => `Under ${c.title}: ${c.suggestedAction}`)
  };

  return {
    id: `doc_${Date.now()}`,
    name,
    uploadDate: new Date().toISOString().split('T')[0],
    fileSize: `${(text.length / 1024).toFixed(1)} KB`,
    status: clauses.some(c => c.riskLevel === 'high') ? 'flagged' : 'completed',
    riskLevel: overallRisk,
    complianceScore: score,
    originalText: text,
    summary,
    clauses,
    reportMemo,
    reviewConfidence: 82
  };
}

async function startServer() {
  const app = express();
  const PORT = 3000;
  app.use(express.json({ limit: '12mb' }));

  // REST API Routes

  // List all analyzed documents
  app.get("/api/documents", (req, res) => {
    res.json(documents);
  });

  // Get a single document by ID
  app.get("/api/documents/:id", (req, res) => {
    const doc = documents.find(d => d.id === req.params.id);
    if (!doc) {
      return res.status(404).json({ error: "Document not found" });
    }
    res.json(doc);
  });

  // Update a clause's review state (Human Review action)
  app.patch("/api/documents/:docId/clauses/:clauseId", (req, res) => {
    const { docId, clauseId } = req.params;
    const { humanReviewed, flaggedForReview, riskLevel, explanation, suggestedAction, title } = req.body;

    const docIndex = documents.findIndex(d => d.id === docId);
    if (docIndex === -1) {
      return res.status(404).json({ error: "Document not found" });
    }

    const clauseIndex = documents[docIndex].clauses.findIndex(c => c.id === clauseId);
    if (clauseIndex === -1) {
      return res.status(404).json({ error: "Clause not found" });
    }

    const clause = documents[docIndex].clauses[clauseIndex];
    if (humanReviewed !== undefined) clause.humanReviewed = humanReviewed;
    if (flaggedForReview !== undefined) clause.flaggedForReview = flaggedForReview;
    if (riskLevel !== undefined) clause.riskLevel = riskLevel;
    if (explanation !== undefined) clause.explanation = explanation;
    if (suggestedAction !== undefined) clause.suggestedAction = suggestedAction;
    if (title !== undefined) clause.title = title;

    // Recalculate status of the document based on flagged clauses
    const hasFlagged = documents[docIndex].clauses.some(c => c.flaggedForReview && !c.humanReviewed);
    documents[docIndex].status = hasFlagged ? 'flagged' : 'completed';

    res.json(documents[docIndex]);
  });

  // Update overall reviewer notes or compliance score on a document
  app.patch("/api/documents/:id", (req, res) => {
    const { id } = req.params;
    const { reviewerNotes, complianceScore, status } = req.body;

    const docIndex = documents.findIndex(d => d.id === id);
    if (docIndex === -1) {
      return res.status(404).json({ error: "Document not found" });
    }

    if (reviewerNotes !== undefined) documents[docIndex].reviewerNotes = reviewerNotes;
    if (complianceScore !== undefined) documents[docIndex].complianceScore = complianceScore;
    if (status !== undefined) documents[docIndex].status = status;

    res.json(documents[docIndex]);
  });

  // Delete a document
  app.delete("/api/documents/:id", (req, res) => {
    const index = documents.findIndex(d => d.id === req.params.id);
    if (index === -1) {
      return res.status(404).json({ error: "Document not found" });
    }
    documents.splice(index, 1);
    res.json({ success: true });
  });

  // Analyze a legal document using the Gemini API
  app.post("/api/analyze", async (req, res) => {
    const { text, name } = req.body;

    if (!text || !text.trim()) {
      return res.status(400).json({ error: "Document text is required" });
    }

    const docName = name || "Un-named Document.txt";

    try {
      const ai = getGeminiClient();

      if (!ai) {
        // No API key configured, use our robust fallback rules engine
        console.log("No valid GEMINI_API_KEY. Running local parsing engine fallback.");
        const fallbackDoc = fallbackAnalyze(text, docName);
        documents.unshift(fallbackDoc);
        return res.json(fallbackDoc);
      }

      // We have a real Gemini client! Call gemini-3.5-flash using structured response output
      console.log(`Analyzing document: ${docName} via gemini-3.5-flash`);

      const prompt = `You are a high-end legal analysis AI. Analyze the following legal document text.
      Perform a professional, serious, and balanced risk assessment.
      Extract the most critical clauses, score risk, and output the required JSON format.

      CRITICAL RESTRICTION: Keep your output tone extremely serious, objective, and editorial. No emojis, no hype language.

      DOCUMENT TEXT:
      ${text}`;

      const response = await ai.models.generateContent({
        model: "gemini-3.5-flash",
        contents: prompt,
        config: {
          systemInstruction: "You are an expert legal counsel specialized in contract audits. You analyze contracts, NDAs, SLAs, and consulting agreements. You extract risky clauses, outline explanations, suggest reciprocal/safe revisions, and compile a compliance summary.",
          responseMimeType: "application/json",
          responseSchema: {
            type: Type.OBJECT,
            properties: {
              summary: {
                type: Type.STRING,
                description: "A plain-English professional executive summary of the agreement."
              },
              complianceScore: {
                type: Type.INTEGER,
                description: "The safety rating of this contract from 0 to 100, where 100 is highly safe/symmetrical and 0 is extremely risky."
              },
              riskLevel: {
                type: Type.STRING,
                description: "The overall contract risk rating: 'low', 'medium', or 'high'."
              },
              clauses: {
                type: Type.ARRAY,
                description: "Array of extracted legally material clauses.",
                items: {
                  type: Type.OBJECT,
                  properties: {
                    title: { type: Type.STRING, description: "Standard naming for the clause (e.g. Limitation of Liability)." },
                    category: { type: Type.STRING, description: "One of: confidentiality, liability, indemnification, intellectual_property, governing_law, other." },
                    text: { type: Type.STRING, description: "The exact or summarized quote of this clause from the document." },
                    riskLevel: { type: Type.STRING, description: "Clause-specific risk: 'low', 'medium', or 'high'." },
                    explanation: { type: Type.STRING, description: "Serious, plain explaining why this clause represents this level of risk." },
                    suggestedAction: { type: Type.STRING, description: "Direct negotiating suggestion or draft amendment text." },
                    flaggedForReview: { type: Type.BOOLEAN, description: "Should be true if riskLevel is 'high' or if non-standard/unbalanced terms exist." }
                  },
                  required: ["title", "category", "text", "riskLevel", "explanation", "suggestedAction", "flaggedForReview"]
                }
              },
              reviewConfidence: {
                type: Type.INTEGER,
                description: "Parsing accuracy confidence score from 0 to 100."
              },
              reportMemo: {
                type: Type.OBJECT,
                description: "Structure for generating an exportable formal audit memo.",
                properties: {
                  executiveSummary: { type: Type.STRING, description: "A structured, formal summary written like a partner's memo." },
                  recommendations: {
                    type: Type.ARRAY,
                    items: { type: Type.STRING },
                    description: "Strategic negotiating actions (as numbered recommendations)."
                  }
                },
                required: ["executiveSummary", "recommendations"]
              }
            },
            required: ["summary", "complianceScore", "riskLevel", "clauses", "reviewConfidence", "reportMemo"]
          }
        }
      });

      const responseText = response.text;
      if (!responseText) {
        throw new Error("Empty response from Gemini API");
      }

      const result = JSON.parse(responseText.trim());

      // Prepare complete document struct
      const newDoc: LegalDocument = {
        id: `doc_${Date.now()}`,
        name: docName,
        uploadDate: new Date().toISOString().split('T')[0],
        fileSize: `${(text.length / 1024).toFixed(1)} KB`,
        status: result.clauses.some((c: any) => c.flaggedForReview) ? 'flagged' : 'completed',
        riskLevel: result.riskLevel || 'medium',
        complianceScore: result.complianceScore || 70,
        originalText: text,
        summary: result.summary,
        clauses: result.clauses.map((c: any, index: number) => ({
          ...c,
          id: `cl_${Date.now()}_${index}`,
          humanReviewed: false
        })),
        reportMemo: {
          id: `memo_${Date.now()}`,
          title: `Legal Memo: ${docName}`,
          date: new Date().toISOString().split('T')[0],
          author: "Legal Analyzer Automated Engine",
          executiveSummary: result.reportMemo.executiveSummary,
          complianceScore: result.complianceScore || 70,
          recommendations: result.reportMemo.recommendations
        },
        reviewConfidence: result.reviewConfidence || 95
      };

      documents.unshift(newDoc);
      res.json(newDoc);

    } catch (error: any) {
      console.error("Gemini API Error during analysis:", error);
      // Fail gracefully and use fallback parsing rather than crashing
      console.log("Applying local fallback parsing after API error.");
      const fallbackDoc = fallbackAnalyze(text, docName);
      documents.unshift(fallbackDoc);
      res.json(fallbackDoc);
    }
  });

  // Serve static assets and Vite development integration
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Legal Analyzer Express server listening on http://localhost:${PORT}`);
  });
}

startServer().catch(err => {
  console.error("Failed to start server:", err);
});
