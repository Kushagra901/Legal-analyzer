"use client";

import React, { useState, useRef } from "react";
import { apiClient } from "@/lib/api";

interface UploadDropzoneProps {
  onUploadSuccess?: (doc: {
    document_id: string;
    filename: string;
    status: string;
    uploaded_at: string;
    storage_path: string;
  }) => void;
}

const ALLOWED_EXTENSIONS = [".pdf", ".txt", ".docx"];
const ALLOWED_MIME_TYPES = [
  "application/pdf",
  "text/plain",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export const UploadDropzone: React.FC<UploadDropzoneProps> = ({ onUploadSuccess }) => {
  const [isDragActive, setIsDragActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const validateFile = (file: File): boolean => {
    const fileExtension = "." + file.name.split(".").pop()?.toLowerCase();
    const isTypeValid =
      ALLOWED_MIME_TYPES.includes(file.type) || ALLOWED_EXTENSIONS.includes(fileExtension);
    if (!isTypeValid) {
      setErrorMessage("Unsupported file type. Only PDF, TXT, and DOCX are allowed.");
      return false;
    }

    if (file.size > MAX_FILE_SIZE) {
      setErrorMessage("File size exceeds maximum limit of 10MB.");
      return false;
    }

    setErrorMessage(null);
    return true;
  };

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    setErrorMessage(null);
    try {
      const data = await apiClient.uploadDocument(file);
      if (onUploadSuccess) {
        onUploadSuccess(data);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to upload document. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true);
    } else if (e.type === "dragleave") {
      setIsDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (validateFile(file)) {
        await handleUpload(file);
      }
    }
  };

  const handleFileInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (validateFile(file)) {
        await handleUpload(file);
      }
    }
  };

  const onButtonClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="w-full">
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={onButtonClick}
        className={`border-2 border-dashed h-48 flex flex-col items-center justify-center text-xs p-6 cursor-pointer transition-all duration-150 rounded-none
          ${isDragActive 
            ? "border-[#0d1b2a] bg-[#faf9f6]" 
            : "border-[#e0dfdb] bg-[#faf9f6] hover:bg-[#f5f4f0]"}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pdf,.txt,.docx"
          onChange={handleFileInputChange}
          disabled={isUploading}
        />
        
        {isUploading ? (
          <div className="flex flex-col items-center">
            <span className="font-semibold text-[#0d1b2a] animate-pulse">
              Uploading and validating file...
            </span>
            <span className="text-[10px] text-[#8a8985] mt-1">Please keep this window open</span>
          </div>
        ) : (
          <>
            <svg
              className="w-8 h-8 text-[#8a8985] mb-3"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="1.5"
                d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <span className="font-semibold text-[#0d1b2a] text-center">
              Drag & drop contract file here, or click to browse
            </span>
            <span className="text-[10px] text-[#8a8985] mt-1">
              PDF, TXT, or DOCX (max. 10MB)
            </span>
          </>
        )}
      </div>

      {errorMessage && (
        <div className="mt-3 p-3 bg-[#faf9f6] border border-[#ff4d4d] text-[#ff4d4d] text-xs flex items-center justify-between">
          <span>{errorMessage}</span>
          <button 
            onClick={() => setErrorMessage(null)} 
            className="text-xs font-bold hover:underline cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
};
