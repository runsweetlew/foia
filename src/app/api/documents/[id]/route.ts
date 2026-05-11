import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { readFile, stat } from "fs/promises";
import path from "path";

const PDF_STORAGE_DIR = process.env.PDF_STORAGE_DIR || "/data/pdfs";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  const meeting = await prisma.meeting.findUnique({
    where: { id },
    select: { pdfStoragePath: true, title: true, meetingDate: true },
  });

  if (!meeting?.pdfStoragePath) {
    return NextResponse.json({ error: "Document not found" }, { status: 404 });
  }

  // Security: ensure the resolved path stays within the storage directory
  const resolvedPath = path.resolve(meeting.pdfStoragePath);
  const resolvedBase = path.resolve(PDF_STORAGE_DIR);
  if (!resolvedPath.startsWith(resolvedBase)) {
    return NextResponse.json({ error: "Invalid path" }, { status: 403 });
  }

  try {
    const fileStat = await stat(resolvedPath);
    const fileBuffer = await readFile(resolvedPath);

    const safeName = (meeting.title || "document")
      .replace(/[^a-zA-Z0-9\-_ ]/g, "")
      .substring(0, 100);
    const dateStr = meeting.meetingDate
      ? new Date(meeting.meetingDate).toISOString().split("T")[0]
      : "unknown";
    const filename = `${safeName}_${dateStr}.pdf`;

    return new NextResponse(fileBuffer, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Length": fileStat.size.toString(),
        "Content-Disposition": `inline; filename="${filename}"`,
        "Cache-Control": "public, max-age=86400, immutable",
      },
    });
  } catch {
    return NextResponse.json({ error: "File not found" }, { status: 404 });
  }
}
