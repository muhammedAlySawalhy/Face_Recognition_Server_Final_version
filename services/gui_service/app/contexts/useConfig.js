'use client';

import { useRuntimeEnv } from './RuntimeEnvContext';

// Compatibility hook for components that previously used config from API
export function useConfig() {
    const runtimeEnv = useRuntimeEnv();

    // Return the same structure as the old API config
    return runtimeEnv;
}

export default useConfig;
