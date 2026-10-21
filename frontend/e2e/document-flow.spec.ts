import { test, expect } from "@playwright/test";
import path from "path";

test.describe("Critical User Flow: Upload Document -> Processing -> View Analysis", () => {
  test.beforeEach(async ({ context }) => {
    // 1. Bypass Supabase Auth for local E2E testing via mock authentication cookie
    await context.addCookies([
      {
        name: "playwright_test_auth",
        value: "true",
        domain: "localhost",
        path: "/",
      },
      {
        name: "auth_token",
        value: "mock-token",
        domain: "localhost",
        path: "/",
      },
    ]);
  });

  test("should upload a sample PDF, transition through processing, and display extracted text in Pane 1", async ({
    page,
  }) => {
    const mockDocId = "test-doc-playwright-1234";
    const sampleFilename = "sample-nda-test-document.pdf";
    const sampleContractText = [
      "MUTUAL NON-DISCLOSURE AGREEMENT",
      "",
      "This Mutual Non-Disclosure Agreement (\"Agreement\") is entered into on October 21, 2026.",
      "1. Confidential Information: Both parties agree to protect proprietary technical data.",
      "2. Term: The term of this Agreement shall be two (2) years from the Effective Date.",
      "3. Governing Law: This Agreement shall be governed by the laws of the State of Delaware.",
      "4. Limitation of Liability: In no event shall either party be liable for consequential damages.",
    ].join("\n");

    let getDocumentCallCount = 0;

    // 2. Mock and simulate the async AI processing pipeline
    await page.route("**/api/v1/documents", async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            document_id: mockDocId,
            filename: sampleFilename,
            status: "processing",
            uploaded_at: new Date().toISOString(),
            storage_path: `documents/${mockDocId}/${sampleFilename}`,
          }),
        });
      } else {
        await route.continue();
      }
    });

    await page.route(`**/api/v1/documents/${mockDocId}/quick-summary`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          document_id: mockDocId,
          filename: sampleFilename,
          quick_summary: "Standard mutual NDA establishing two-year confidentiality under Delaware law.",
          document_type: "Mutual Non-Disclosure Agreement",
          key_points: [
            "2-year confidentiality duration",
            "Mutual protection of proprietary technical data",
            "Delaware jurisdiction",
          ],
          estimated_risk_level: "LOW",
          disclaimer: "This AI response assists review and is not legal advice.",
        }),
      });
    });

    await page.route(`**/api/v1/documents/${mockDocId}`, async (route) => {
      getDocumentCallCount++;

      // Simulate async progression: initial fetch returns processing, subsequent poll returns completed
      if (getDocumentCallCount === 1) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            document_id: mockDocId,
            filename: sampleFilename,
            status: "processing",
            uploaded_at: new Date().toISOString(),
            original_text: null,
            extracted_text: null,
            analysis: {
              summary: "Processing document analysis...",
              safety_score: null,
              risk_level: "LOW",
              clauses: [],
              extracted_text: null,
            },
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            document_id: mockDocId,
            filename: sampleFilename,
            status: "completed",
            uploaded_at: new Date().toISOString(),
            original_text: sampleContractText,
            extracted_text: sampleContractText,
            analysis: {
              summary: "Mutual non-disclosure agreement with 2-year confidentiality term and Delaware governing law.",
              safety_score: 95,
              risk_level: "LOW",
              clauses: [
                {
                  id: "clause-confidentiality-1",
                  type: "Confidentiality",
                  text: "Both parties agree to protect proprietary technical data.",
                  explanation: "Standard mutual confidentiality protection obligation.",
                  risk_level: "LOW",
                },
                {
                  id: "clause-term-2",
                  type: "Term",
                  text: "The term of this Agreement shall be two (2) years from the Effective Date.",
                  explanation: "Standard 2-year duration for technical disclosure.",
                  risk_level: "LOW",
                },
              ],
              citations: [],
              compliance_checks: [],
              extracted_text: sampleContractText,
              original_text: sampleContractText,
            },
          }),
        });
      }
    });

    // 3. Step 1: Navigate to the upload page
    await page.goto("/documents/upload");
    await expect(page.locator("h1")).toContainText("Upload Contract Document");

    // 4. Step 2: Upload sample PDF from /test-documents
    const testDocPath = path.resolve(__dirname, "../../test-documents", sampleFilename);
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testDocPath);

    // 5. Step 3: Assert upload success state and instant summary card
    await expect(page.locator("text=Upload Ingested Successfully")).toBeVisible({ timeout: 15000 });
    await expect(page.locator("text=Mutual Non-Disclosure Agreement")).toBeVisible();

    // 6. Step 4: Navigate to the document review / analysis page
    const openReviewButton = page.getByRole("button", { name: "Open Full Review →" });
    await openReviewButton.click();

    await page.waitForURL(`**/documents/${mockDocId}`);

    // 7. Step 5: Assert that Pane 1 displays the extracted contract text
    const pane1 = page.getByTestId("pane-1-extracted-document");
    await expect(pane1).toBeVisible();
    await expect(pane1.locator("text=Pane 1: Extracted Document Text")).toBeVisible();

    // Assert that the extracted contract text lines are rendered inside Pane 1
    await expect(pane1.getByText("MUTUAL NON-DISCLOSURE AGREEMENT", { exact: true })).toBeVisible({ timeout: 15000 });
    await expect(pane1.getByText("Both parties agree to protect proprietary technical data.")).toBeVisible();
    await expect(pane1.getByText("Delaware")).toBeVisible();

    // Assert that the bug message is NOT present anywhere on the page or in Pane 1
    await expect(page.locator("text=Extracted contract text unavailable.")).not.toBeVisible();

    // 8. Step 6: Verify identified clauses in Pane 2
    await expect(page.locator("text=Confidentiality").first()).toBeVisible();
    await expect(page.locator("text=Contract Risk Score Summary")).toBeVisible();
    await expect(page.locator("text=95 / 100")).toBeVisible();
  });
});
