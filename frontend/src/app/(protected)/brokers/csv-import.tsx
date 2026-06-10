"use client";
import { useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import * as XLSX from "xlsx";
import { Upload, Download, FileSpreadsheet, Loader2, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  const [fileError, setFileError] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);

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

  const processFile = useCallback((file: File) => {
    const lower = file.name.toLowerCase();
    const isCSV = lower.endsWith(".csv");
    const isExcel = lower.endsWith(".xlsx") || lower.endsWith(".xls");

    if (!isCSV && !isExcel) {
      setFileError("Please upload a .csv, .xlsx, or .xls file");
      return;
    }
    setFileError("");
    setFileName(file.name);

    const reader = new FileReader();
    if (isCSV) {
      reader.onload = (event) => {
        setCSVContent(event.target?.result as string);
      };
      reader.readAsText(file);
    } else {
      // Excel: convert the first sheet to CSV in the browser so the
      // backend import contract stays the same.
      reader.onload = (event) => {
        try {
          const data = event.target?.result as ArrayBuffer;
          const workbook = XLSX.read(data, { type: "array" });
          const sheetName = workbook.SheetNames[0];
          if (!sheetName) {
            setFileError("The Excel file has no sheets");
            return;
          }
          const csv = XLSX.utils.sheet_to_csv(workbook.Sheets[sheetName]);
          if (!csv.trim()) {
            setFileError("The Excel sheet is empty");
            return;
          }
          setCSVContent(csv);
        } catch {
          setFileError("Could not read the Excel file. Make sure it isn't corrupted or password-protected.");
        }
      };
      reader.readAsArrayBuffer(file);
    }
  }, []);

  const handleFileUpload = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) processFile(file);
    },
    [processFile]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files?.[0];
      if (file) processFile(file);
    },
    [processFile]
  );

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
      setFileError("Please upload a CSV or Excel file first");
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
    <div className="space-y-4 min-w-0">
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
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          className={cn(
            "flex flex-col items-center justify-center w-full min-w-0 h-28 px-3 border-2 border-dashed rounded-lg cursor-pointer transition-colors box-border",
            isDragOver
              ? "border-primary bg-primary/5"
              : "border-border hover:bg-muted/50"
          )}
        >
          {fileName ? (
            <div className="flex items-center gap-2 w-full min-w-0 max-w-full text-sm">
              <FileSpreadsheet className="h-5 w-5 shrink-0 text-emerald-600" />
              <span className="font-medium truncate min-w-0 text-center" title={fileName}>
                {fileName}
              </span>
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
            </div>
          ) : (
            <div className="flex flex-col items-center gap-1 text-muted-foreground">
              <Upload className="h-6 w-6" />
              <p className="text-sm">Click to upload CSV or Excel</p>
              <p className="text-xs">.csv, .xlsx, .xls — or drag and drop</p>
            </div>
          )}
          <input
            id="csv-upload"
            type="file"
            accept=".csv,.xlsx,.xls"
            className="hidden"
            onChange={handleFileUpload}
          />
        </label>
      </div>

      {/* Step 3: Cash balance + import */}
      <form
        onSubmit={(e) => { e.preventDefault(); handleSubmit(onSubmit)(); }}
        className="space-y-4 min-w-0"
      >
        <div className="space-y-2 min-w-0">
          <Label htmlFor="cash_balance">Cash Balance (optional)</Label>
          <Input
            id="cash_balance"
            type="number"
            step="0.01"
            placeholder="0.00"
            className="w-full min-w-0"
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

        <Button
          type="submit"
          className="w-full min-w-0 shrink-0"
          disabled={!csvContent || connectMutation.isPending}
        >
          {connectMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Import Portfolio
        </Button>
      </form>
    </div>
  );
}
