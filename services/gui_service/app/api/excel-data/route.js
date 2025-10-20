import { NextResponse } from 'next/server';
import * as XLSX from 'xlsx';
import fs from 'fs';
import path from 'path';

export async function GET() {
    try {
        // Look for Excel files in the workspace
        const possiblePaths = [
            process.env.EXCEL_PATH
        ]

        let excelFilePath = null;
        for (const filePath of possiblePaths) {
            try {
                if (fs.existsSync(filePath)) {
                    // Check if file is accessible and not empty
                    const stats = fs.statSync(filePath);
                    if (stats.size > 0) {
                        excelFilePath = filePath;
                        break;
                    }
                }
            } catch (error) {
                console.log(`Error checking file ${filePath}:`, error.message);
                continue;
            }
        }

        if (!excelFilePath) {
            console.log('Excel file not found at any of these paths:', possiblePaths);

            // Fallback: Create sample data based on existing users
            const sampleUsers = [
                {
                    username: 'ci-user296',
                    nationalId: '26612181400520',
                    name: 'علاء محمد أحمد محمد',
                    department: 'أمين شرطة',
                    government: 'مديرية أمن القاهرة'
                },
                {
                    username: 'ci-user261',
                    nationalId: '26612181400521',
                    name: 'علاء أحمد السيد أحمد',
                    department: 'أمين شرطة',
                    government: 'مديرية أمن القاهرة'
                },
                {
                    username: 'ci_aly1',
                    nationalId: '98765432109876',
                    name: 'Ali Hassan Ibrahim',
                    department: 'Human Resources',
                    government: 'Cairo'
                }
            ];

            return NextResponse.json({
                success: true,
                users: sampleUsers,
                count: sampleUsers.length,
                filePath: 'fallback-sample-data',
                note: 'Using sample data - Excel file not found'
            });
        }

        console.log('Found Excel file at:', excelFilePath);

        let workbook, data;
        try {
            // Read the Excel file
            workbook = XLSX.readFile(excelFilePath);
            const sheetName = workbook.SheetNames[0]; // Use first sheet
            const worksheet = workbook.Sheets[sheetName];

            // Read as array of arrays since there are no headers
            const rawData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

            // Transform to proper format - columns are: username, nationalId, name, department, government, id
            data = rawData.map(row => {
                if (!row || row.length < 5) return null; // Skip empty or incomplete rows

                return {
                    username: String(row[0] || '').trim(),
                    nationalId: String(row[1] || ''),
                    name: String(row[2] || '').trim(),
                    department: String(row[3] || '').trim(),
                    government: String(row[4] || '').trim(),
                    id: row[5] || ''
                };
            }).filter(user => user && user.username); // Filter out null/empty entries

        } catch (readError) {
            console.error('Error reading Excel file:', readError.message);

            // Fallback: Create sample data if Excel read fails
            const sampleUsers = [
                {
                    username: 'ci-user296',
                    nationalId: '26612181400520',
                    name: 'علاء محمد أحمد محمد',
                    department: 'أمين شرطة',
                    government: 'مديرية أمن القاهرة'
                },
                {
                    username: 'ci-user261',
                    nationalId: '26612181400521',
                    name: 'علاء أحمد السيد أحمد',
                    department: 'أمين شرطة',
                    government: 'مديرية أمن القاهرة'
                },
                {
                    username: 'ci_aly1',
                    nationalId: '98765432109876',
                    name: 'Ali Hassan Ibrahim',
                    department: 'Human Resources',
                    government: 'Cairo'
                }
            ];

            return NextResponse.json({
                success: true,
                users: sampleUsers,
                count: sampleUsers.length,
                filePath: 'fallback-sample-data',
                note: 'Using sample data - Excel file read error: ' + readError.message
            });
        }

        console.log(`Loaded ${data.length} users from Excel file`);
        console.log('Sample data:', data[0]);

        // Data is already in the correct format
        const users = data;

        return NextResponse.json({
            success: true,
            users,
            count: users.length,
            filePath: excelFilePath
        });

    } catch (error) {
        console.error('Error reading Excel file:', error);
        return NextResponse.json({
            success: false,
            error: error.message
        }, { status: 500 });
    }
}
