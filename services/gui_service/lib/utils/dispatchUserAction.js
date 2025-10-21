/**
 * dispatchUserAction
 * Sends status updates via the internal multi-server route.
 * This centralizes the multi-server logic and provides better error handling.
 *
 * @param {Object} opts
 * @param {string} opts.username
 * @param {string} opts.action  // e.g. 'pause' | 'block' | 'normal'
 * @returns {Promise<Object>} returns the response data on success
 * @throws {Error} throws if the update failed on all servers
 */
export default async function dispatchUserAction({ username, action } = {}) {
    if (!username) throw new Error('username is required');
    if (!action) throw new Error('action is required');

    const payload = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, status: action }),
    };

    try {
        const response = await fetch('/api/multi/client/status/update', payload);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }

        // Check if at least one server succeeded
        const anySuccess = (data.s1 && data.s1.ok) || (data.s2 && data.s2.ok);

        if (!anySuccess) {
            const details = [];
            if (data.s1) details.push(`S1: HTTP ${data.s1.status}`);
            if (data.s2) details.push(`S2: HTTP ${data.s2.status}`);
            throw new Error(`Update failed on all servers: ${details.join(', ')}`);
        }

        return data;
    } catch (error) {
        // Re-throw with more context
        const message = error.message || 'Unknown error occurred';
        const err = new Error(`dispatchUserAction failed: ${message}`);
        err.originalError = error;
        throw err;
    }
}
