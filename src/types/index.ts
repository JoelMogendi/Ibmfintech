// src/types/index.ts

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export type PaymentChannel = 'mpesa' | 'bank' | 'ussd';

export type RecommendedAction = 
  | 'allow' 
  | 'monitor_and_verify' 
  | 'enhanced_due_diligence' 
  | 'hold_and_investigate';

export interface ScoredTransaction {
  transaction_id: string;
  account_id: string;
  customer_id: string;
  payment_date: string; // ISO date string: YYYY-MM-DD
  amount_paid: number;
  channel: PaymentChannel;
  risk_score: number;   // 0.0 to 100.0
  risk_level: RiskLevel;
  anomaly_type: string;
  risk_reasons: string[];
  recommended_action: RecommendedAction;
}

export interface ModelMetrics {
  records_scored: number;
  injected_anomalies: number;
  investigation_threshold: number;
  precision: number;
  recall: number;
  f1_score: number;
  accuracy: number;
  roc_auc: number;
  confusion_matrix: number[][];
  methodology: string;
  evaluation_note: string;
}