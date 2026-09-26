import { NextResponse } from "next/server";
import fs from 'fs';
import path from "path";
import { ScoredTransaction } from "@/types";

export async function GET(req: Request) {
    try {
        const { searchParams } = new URL(req.url);
        const level = searchParams.get('level');
        const channel = searchParams.get('channel');

        // attempt to load full pipeline output
        const primaryPath = path.join(process.cwd(), 'data-science', 'data', 'generated', 'scored_transaction.json');
        const samplePath = path.join(process.cwd(), 'data-science', 'demo', 'scored_transactions.sample.json');

        const filePath = fs.existsSync(primaryPath) ? primaryPath : samplePath;

        if (!fs.existsSync(filePath)) {
            return NextResponse.json(
                { error: "Dataset not found. Run pipeline or provide sample." },
                { status: 404 }
            );
        };

        const rawData = fs.readFileSync(filePath, 'utf-8');
        let transactions: ScoredTransaction[] = JSON.parse(rawData);

        // filter by risk level
        if(level) {
            transactions = transactions.filter(
                (tx) => tx.channel.toLowerCase() === channel?.toLowerCase()
            );
        };

        return NextResponse.json({
            total: transactions.length,
            data: transactions,
        });
    } catch (error) {
        console.error("Failed to retrieve transactions", error);
        return NextResponse.json(
            { error: "Internal Server Error" },
            { status: 500 }
        );
    }
};