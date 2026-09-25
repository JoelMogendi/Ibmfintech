import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { ModelMetrics } from "@/types";

export async function GET() {
    try {
        const metricsPath = path.join(process.cwd(), 'data-science', 'data', 'generated', 'model_metrics.json');

        if(!fs.existsSync(metricsPath)) {
            return NextResponse.json(
                { message: "Metrics  not yet generated. Run run_pipeline.py first." },
                { status: 404 }
            );
        };

         const rawData = fs.readFileSync(metricsPath, 'utf-8');
         const metrics : ModelMetrics = JSON.parse(rawData);

         return NextResponse.json(metrics);
    } catch (error) {
        console.error("Failed to read model metrics:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    };
};