import { NextResponse } from "next/server";
import path from "path";
import fs from "fs/promises";

// File serving should not be cached when path is dynamic
export const revalidate = 0;

export async function GET() {
    try {
        // Read Excel file path from environment variable
        const excelPath = process.env.EXCEL_PATH || path.join(process.cwd(), "public", "data", "users.xlsx");
        const fileBuffer = await fs.readFile(excelPath);


        return new NextResponse(fileBuffer, {
            status: 200,
            headers: {
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "Content-Disposition": "attachment; filename=users.xlsx"
            }
        });
    } catch (e) {
        return NextResponse.json({ error: "Excel file not found" }, { status: 404 });
    }
}
