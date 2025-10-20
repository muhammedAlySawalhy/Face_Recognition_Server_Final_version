import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
    const s1 = process.env.S1_GET_URL || process.env.S1_GET;
    const s2 = process.env.S2_GET_URL || process.env.S2_GET;

    if (!s1 || !s2) {
        return NextResponse.json({ error: 'Missing S1_GET_URL/S1_GET or S2_GET_URL/S2_GET in env' }, { status: 500 });
    }

    const qs = req.nextUrl.search || '';

    try {
        const results = await Promise.allSettled<globalThis.Response>([
            fetch(`${s1}${qs}`, { cache: 'no-store', headers: { Accept: 'application/json' } }),
            fetch(`${s2}${qs}`, { cache: 'no-store', headers: { Accept: 'application/json' } }),
        ]);

        let s1Resp: any = null, s2Resp: any = null;

        if (results[0].status === 'fulfilled') {
            const r1 = results[0].value;
            let d1: any = null;
            try {
                const ct = r1.headers.get('content-type') || '';
                d1 = ct.includes('application/json') ? await r1.json().catch(() => null) : await r1.text().catch(() => null);
            } catch {
                d1 = null;
            }
            s1Resp = { status: r1.status, ok: r1.ok, data: d1 };
        } else {
            s1Resp = { status: null, ok: false, error: 'Server down or unreachable' };
        }

        if (results[1].status === 'fulfilled') {
            const r2 = results[1].value;
            let d2: any = null;
            try {
                const ct = r2.headers.get('content-type') || '';
                d2 = ct.includes('application/json') ? await r2.json().catch(() => null) : await r2.text().catch(() => null);
            } catch {
                d2 = null;
            }
            s2Resp = { status: r2.status, ok: r2.ok, data: d2 };
        } else {
            s2Resp = { status: null, ok: false, error: 'Server down or unreachable' };
        }

        return NextResponse.json({ s1: s1Resp, s2: s2Resp });
    } catch (e: any) {
        return NextResponse.json({ error: 'Upstream fetch failed', message: String(e) }, { status: 502 });
    }
}

export async function POST(req: NextRequest) {
    const s1 = process.env.S1_GET_URL || process.env.S1_GET;
    const s2 = process.env.S2_GET_URL || process.env.S2_GET;

    if (!s1 || !s2) {
        return NextResponse.json({ error: 'Missing S1_GET_URL/S1_GET or S2_GET_URL/S2_GET in env' }, { status: 500 });
    }

    const qs = req.nextUrl.search || '';
    const contentType = req.headers.get('content-type') || undefined;
    const auth = req.headers.get('authorization') || undefined;
    const body = await req.arrayBuffer();

    try {
        const results = await Promise.allSettled<globalThis.Response>([
            fetch(`${s1}${qs}`, { method: 'POST', body, headers: { ...(contentType ? { 'content-type': contentType } : {}), ...(auth ? { authorization: auth } : {}), Accept: 'application/json' } }),
            fetch(`${s2}${qs}`, { method: 'POST', body, headers: { ...(contentType ? { 'content-type': contentType } : {}), ...(auth ? { authorization: auth } : {}), Accept: 'application/json' } }),
        ]);

        let s1Resp: any = null, s2Resp: any = null;

        if (results[0].status === 'fulfilled') {
            const r1 = results[0].value;
            let d1: any = null;
            try {
                const ct = r1.headers.get('content-type') || '';
                d1 = ct.includes('application/json') ? await r1.json().catch(() => null) : await r1.text().catch(() => null);
            } catch {
                d1 = null;
            }
            s1Resp = { status: r1.status, ok: r1.ok, data: d1 };
        } else {
            s1Resp = { status: null, ok: false, error: 'Server down or unreachable' };
        }

        if (results[1].status === 'fulfilled') {
            const r2 = results[1].value;
            let d2: any = null;
            try {
                const ct = r2.headers.get('content-type') || '';
                d2 = ct.includes('application/json') ? await r2.json().catch(() => null) : await r2.text().catch(() => null);
            } catch {
                d2 = null;
            }
            s2Resp = { status: r2.status, ok: r2.ok, data: d2 };
        } else {
            s2Resp = { status: null, ok: false, error: 'Server down or unreachable' };
        }

        return NextResponse.json({ s1: s1Resp, s2: s2Resp });
    } catch (e: any) {
        return NextResponse.json({ error: 'Upstream fetch failed', message: String(e) }, { status: 502 });
    }
}
