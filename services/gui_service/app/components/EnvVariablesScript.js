import { unstable_noStore as noStore } from 'next/cache';
import { runtimeEnvConfig } from '../config.js';

export default function EnvVariablesScript() {
    noStore();

    return (
        <script
            id="env-config"
            dangerouslySetInnerHTML={{
                __html: `window.__ENV__ = ${JSON.stringify(runtimeEnvConfig)};`,
            }}
        />
    );
}
