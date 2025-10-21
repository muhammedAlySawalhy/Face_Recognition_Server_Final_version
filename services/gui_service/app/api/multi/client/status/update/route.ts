import { NextRequest, NextResponse } from 'next/server';

async function forward(method: 'POST' | 'PUT' | 'PATCH', req: NextRequest) {
    const s1 = process.env.S1_UPDATE_URL;
    const s2 = process.env.S2_UPDATE_URL;
    if (!s1 || !s2) {
        return NextResponse.json({ error: 'Missing S1_UPDATE_URL or S2_UPDATE_URL in env' }, { status: 500 });
    }

    const qs = req.nextUrl.search || '';
    const contentType = req.headers.get('content-type') || undefined;
    const auth = req.headers.get('authorization') || undefined;
    const body = await req.arrayBuffer(); // cloneable buffer so we can send to both

    try {
        const results = await Promise.allSettled([
            fetch(`${s1}${qs}`, { method, body, headers: { ...(contentType ? { 'content-type': contentType } : {}), ...(auth ? { authorization: auth } : {}), Accept: 'application/json' } }),
            fetch(`${s2}${qs}`, { method, body, headers: { ...(contentType ? { 'content-type': contentType } : {}), ...(auth ? { authorization: auth } : {}), Accept: 'application/json' } }),
        ]);

        // Prepare response objects for s1 and s2
        let s1Resp = null, s2Resp = null;

        // Handle S1
        if (results[0].status === 'fulfilled') {
            const r1 = results[0].value;
            let d1;
            try {
                d1 = r1.headers.get('content-type')?.includes('application/json') ? await r1.json().catch(() => null) : await r1.text().catch(() => null);
            } catch {
                d1 = null;
            }
            s1Resp = { status: r1.status, ok: r1.ok, data: d1 };
        } else {
            s1Resp = { status: null, ok: false, error: 'Server down or unreachable' };
        }

        // Handle S2
        if (results[1].status === 'fulfilled') {
            const r2 = results[1].value;
            let d2;
            try {
                d2 = r2.headers.get('content-type')?.includes('application/json') ? await r2.json().catch(() => null) : await r2.text().catch(() => null);
            } catch {
                d2 = null;
            }
            s2Resp = { status: r2.status, ok: r2.ok, data: d2 };
        } else {
            s2Resp = { status: null, ok: false, error: 'Server down or unreachable' };
        }

        return NextResponse.json({
            s1: s1Resp,
            s2: s2Resp,
        });
    } catch (e: any) {
        return NextResponse.json({ error: 'Upstream update failed', message: String(e) }, { status: 502 });
    }
}

export async function POST(req: NextRequest) { return forward('POST', req); }
export async function PUT(req: NextRequest) { return forward('PUT', req); }
export async function PATCH(req: NextRequest) { return forward('PATCH', req); }
