"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import { FileUp, FileText, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/common/empty-state";
import { Skeleton } from "@/components/common/skeleton";
import { useDocuments, useUploadDocument } from "@/lib/queries/documents";
import { cn } from "@/lib/utils";

const STATUS_ICON = {
  processing: <Loader2 className="size-4 animate-spin text-brand-cyan" />,
  extracted: <CheckCircle2 className="size-4 text-success" />,
  needs_review: <AlertCircle className="size-4 text-warning" />,
  failed: <AlertCircle className="size-4 text-danger" />,
};

export default function DocumentsPage() {
  const { data: documents, isLoading } = useDocuments();
  const upload = useUploadDocument();
  const [kind, setKind] = useState<"policy" | "statement" | "id_proof" | "other">("policy");

  const onDrop = useCallback(
    async (files: File[]) => {
      const file = files[0];
      if (!file) return;
      try {
        await upload.mutateAsync({ file, kind });
        toast.success("Document uploaded — extracting fields…");
      } catch {
        toast.error("Could not reach the backend yet — try again once it's running.");
      }
    },
    [upload, kind],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"], "image/png": [".png"], "image/jpeg": [".jpg", ".jpeg"] },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-text sm:text-3xl">Documents</h1>
        <p className="text-sm text-muted">Upload policy documents — our AI reads the fine print for you.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Upload a document</CardTitle>
          <CardDescription>Text or scanned PDF, up to 10 MB.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {(["policy", "statement", "id_proof", "other"] as const).map((k) => (
              <button
                key={k}
                onClick={() => setKind(k)}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs font-medium capitalize",
                  kind === k ? "border-brand-cyan bg-cyan-soft text-brand-navy dark:text-brand-cyan" : "border-border text-muted",
                )}
              >
                {k.replace("_", " ")}
              </button>
            ))}
          </div>
          <div
            {...getRootProps()}
            className={cn(
              "flex h-32 cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border-2 border-dashed text-center text-sm text-muted transition-colors",
              isDragActive ? "border-brand-cyan bg-cyan-soft" : "border-border hover:bg-surface-2",
            )}
          >
            <input {...getInputProps()} />
            {upload.isPending ? (
              <Loader2 className="size-6 animate-spin text-brand-cyan" />
            ) : (
              <>
                <FileUp className="size-6" />
                <span>Drag & drop, or click to browse</span>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Your documents</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {isLoading ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-14" />)
          ) : !documents || documents.length === 0 ? (
            <EmptyState icon={FileText} title="No documents yet" body="Upload your first policy to get started." />
          ) : (
            documents.map((doc) => (
              <div key={doc.id} className="flex items-center justify-between rounded-lg border border-border p-3">
                <div className="flex items-center gap-3">
                  {STATUS_ICON[doc.status]}
                  <div>
                    <p className="text-sm font-medium text-text capitalize">{doc.kind.replace("_", " ")}</p>
                    <p className="text-xs text-muted">
                      {new Date(doc.created_at).toLocaleDateString("en-IN")}
                    </p>
                  </div>
                </div>
                <Badge variant={doc.status === "extracted" ? "success" : doc.status === "failed" ? "destructive" : "outline"}>
                  {doc.status.replace("_", " ")}
                </Badge>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
