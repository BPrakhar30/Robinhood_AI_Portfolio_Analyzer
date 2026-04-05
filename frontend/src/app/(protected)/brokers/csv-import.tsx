"use client";
import { useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Upload, Download, FileSpreadsheet, Loader2, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import { useConnectCSV, useCSVTemplate } from "@/features/brokers/hooks";

interface FormData {
  cash_balance: number;
}

const schema = z.object({
  cash_balance: z.preprocess(
    (v) => (v === "" || v === undefined ? 0 : Number(v)),
    z.number().min(0, "Cash balance cannot be negative")
  ),
});

interface Props {
  onSuccess: () => void;
}

export function CSVImportForm({ onSuccess }: Props) {
  const [csvContent, setCSVContent] = useState("");
  const [fileName, setFileName] = useState("");
  const [preview, setPreview] = useState<string[]>([]);
  const [fileError, setFileError] = useState("");

  const connectMutation = useConnectCSV();
  const { data: templateData } = useCSVTemplate();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema) as any,
    defaultValues: { cash_balance: 0 },
  });

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith(".csv")) {
      setFileError("Please upload a .csv file");
      return;
    }
    setFileError("");

    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      setCSVContent(text);

      const lines = text.trim().split("\n");
      setPreview(lines.slice(0, 4));
    };
    reader.readAsText(file);
  }, []);

  const handleDownloadTemplate = () => {
    if (!templateData) return;
    const blob = new Blob([templateData.template], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "portfolio_template.csv";
    a.click();
    URL.revokeObjectURL(url);
    // Template download initiated via browser
  };

  const onSubmit = async (data: FormData) => {
    if (!csvContent) {
      setFileError("Please upload a CSV file first");
      return;
    }

    try {
      await connectMutation.mutateAsync({
        csv_content: csvContent,
        cash_balance: data.cash_balance,
        filename: fileName || "upload.csv",
      });
      onSuccess();
    } catch {
      // Error is shown inline via connectMutation.isError
    }
  };

  return (
    <div className="space-y-4">
      {/* Step 1: Download template */}
      <div className="space-y-2">
        <p className="text-sm font-medium">Step 1: Download template</p>
        <Button
          variant="outline"
          size="sm"
          onClick={handleDownloadTemplate}
          disabled={!templateData}
        >
          <Download className="mr-2 h-3.5 w-3.5" />
          Download CSV Template
        </Button>
        <p className="text-xs text-muted-foreground">
          Required columns: <code className="text-xs">symbol</code>, <code className="text-xs">quantity</code>, <code className="text-xs">average_cost</code>
        </p>
      </div>

      {/* Step 2: Upload file */}
      <div className="space-y-2">
        <p className="text-sm font-medium">Step 2: Upload your file</p>
        <label
          htmlFor="csv-upload"
          className="flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-border rounded-lg cursor-pointer hover:bg-muted/50 transition-colors"
        >
          {fileName ? (
            <div className="flex items-center gap-2 text-sm">
              <FileSpreadsheet className="h-5 w-5 text-emerald-600" />
              <span className="font-medium">{fileName}</span>
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            </div>
          ) : (
            <div className="flex flex-col items-center gap-1 text-muted-foreground">
              <Upload className="h-6 w-6" />
              <p className="text-sm">Click to upload CSV</p>
              <p className="text-xs">or drag and drop</p>
            </div>
          )}
          <input
            id="csv-upload"
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleFileUpload}
          />
        </label>
      </div>

      {/* Preview */}
      {preview.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium">Preview</p>
          <div className="bg-muted rounded-lg p-3 overflow-x-auto">
            <pre className="text-xs font-mono whitespace-pre">
              {preview.map((line, i) => (
                <div key={i} className={i === 0 ? "font-semibold text-foreground" : "text-muted-foreground"}>
                  {line}
                </div>
              ))}
              {preview.length < csvContent.trim().split("\n").length && (
                <div className="text-muted-foreground/50 mt-1">
                  ... {csvContent.trim().split("\n").length - preview.length} more rows
                </div>
              )}
            </pre>
          </div>
        </div>
      )}

      {/* Step 3: Cash balance + import */}
      <form onSubmit={(e) => { e.preventDefault(); handleSubmit(onSubmit)(); }} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="cash_balance">Cash Balance (optional)</Label>
          <Input
            id="cash_balance"
            type="number"
            step="0.01"
            placeholder="0.00"
            {...register("cash_balance")}
          />
          {errors.cash_balance && (
            <p className="text-xs text-destructive">{errors.cash_balance.message}</p>
          )}
        </div>

        {fileError && (
          <Alert variant="destructive">
            <AlertDescription className="text-sm">{fileError}</AlertDescription>
          </Alert>
        )}

        {connectMutation.isError && (
          <Alert variant="destructive">
            <AlertDescription className="text-sm">
              {(connectMutation.error as Error)?.message || "Import failed. Check your CSV format."}
            </AlertDescription>
          </Alert>
        )}

        <button type="submit" className={cn(buttonVariants(), "w-full")} disabled={!csvContent || connectMutation.isPending}>
          {connectMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Import Portfolio
        </button>
      </form>
    </div>
  );
}
