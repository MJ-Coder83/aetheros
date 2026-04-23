/**
 * Catch-all API proxy — forwards requests from /api/* to the FastAPI backend.
 *
 * This avoids CORS issues during development. In production you'd use
 * a reverse proxy (nginx, traefik) instead.
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path?: string[] }> },
) {
  const { path } = await params;
  const backendPath = (path ?? []).join("/");
  const url = `${BACKEND_URL}/${backendPath}${request.nextUrl.search}`;
  const res = await fetch(url, { headers: buildHeaders(request) });
  return forward(res);
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path?: string[] }> },
) {
  const { path } = await params;
  const backendPath = (path ?? []).join("/");
  const url = `${BACKEND_URL}/${backendPath}${request.nextUrl.search}`;
  const body = await request.text();
  const res = await fetch(url, {
    method: "POST",
    headers: buildHeaders(request),
    body,
  });
  return forward(res);
}

/* ── helpers ──────────────────────────────────────────────────── */

function buildHeaders(request: NextRequest): HeadersInit {
  const headers = new Headers();
  headers.set("Content-Type", "application/json");
  const auth = request.headers.get("authorization");
  if (auth) headers.set("Authorization", auth);
  return headers;
}

function forward(res: Response): NextResponse {
  return new NextResponse(res.body, {
    status: res.status,
    headers: res.headers,
  });
}
