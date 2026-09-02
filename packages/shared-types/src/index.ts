export interface PredictRequest { prompt: string; params?: Record<string, unknown>; modelVersion?: string; }
export interface PredictResponse { result: string; tokensIn: number; tokensOut: number; latencyMs: number; modelVersion: string; cached: boolean; }
export type Role = "owner" | "admin" | "member";
export type Plan = "free" | "pro" | "enterprise";
