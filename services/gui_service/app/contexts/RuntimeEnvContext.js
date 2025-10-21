'use client';

import { createContext, useContext, useState, useEffect } from 'react';

const defaultEnvVariables = {
    guiData: '/app/gui_data',
    userDatabase: '/app/users_db',
    actions: '/app/actions',
    endpoints: {
        s1Get: '',
        s2Get: '',
        s1Update: '',
        s2Update: ''
    }
};

const RuntimeEnvContext = createContext(defaultEnvVariables);

export const envScriptId = 'env-config';

const isSSR = typeof window === 'undefined';

export const getRuntimeEnv = () => {
    if (isSSR) return defaultEnvVariables;

    // Check if window.__ENV__ is available (injected by script tag)
    if (window.__ENV__) {
        return window.__ENV__;
    }

    // Fallback: try to read from script tag
    const script = window.document.getElementById(envScriptId);
    if (script) {
        try {
            return JSON.parse(script.innerText);
        } catch (error) {
            console.error('Error parsing env config from script tag:', error);
        }
    }

    return defaultEnvVariables;
};

export function RuntimeEnvProvider({ children }) {
    const [envs, setEnvs] = useState(defaultEnvVariables);

    useEffect(() => {
        const runtimeEnvs = getRuntimeEnv();
        setEnvs(runtimeEnvs);
    }, []);

    return (
        <RuntimeEnvContext.Provider value={envs}>
            {children}
        </RuntimeEnvContext.Provider>
    );
}

export const useRuntimeEnv = () => {
    const context = useContext(RuntimeEnvContext);
    if (context === undefined) {
        throw new Error('useRuntimeEnv must be used within a RuntimeEnvProvider');
    }
    return context;
};
