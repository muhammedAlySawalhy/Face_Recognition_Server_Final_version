#!/usr/bin/env node

/**
 * Simple Redis Mock Data Generator
 * Creates sample data that matches the exact structure expected by the Dashboard
 */

// Government prefixes for realistic usernames
const GOV_PREFIXES = ['ci', 'gz', 'ax', 'an', 'lx', 'kh', 'mn', 'bh', 'bn', 'dk'];

// Generate random usernames with government prefixes
function generateUsername(prefix) {
    const names = ['ahmed', 'mohamed', 'sara', 'fatma', 'omar', 'ali', 'zeinab', 'hussein', 'mona', 'hassan'];
    const numbers = Math.floor(Math.random() * 999) + 100;
    const name = names[Math.floor(Math.random() * names.length)];
    return `${prefix}_${name}${numbers}`;
}

// Generate sample data for each server
function generateServerData(serverName, govPrefixes) {
    const activeCount = Math.floor(Math.random() * 10) + 5; // 5-15 active clients
    const deactivatedCount = Math.floor(Math.random() * 5) + 1; // 1-5 deactivated
    const pausedCount = Math.floor(Math.random() * 3) + 1; // 1-3 paused  
    const blockedCount = Math.floor(Math.random() * 3) + 1; // 1-3 blocked
    const errorCount = Math.floor(Math.random() * 4) + 1; // 1-4 connection errors

    const active_clients = [];
    const deactivate_clients = [];
    const paused_clients = [];
    const blocked_clients = [];
    const connecting_internet_error = [];

    // Generate active clients
    for (let i = 0; i < activeCount; i++) {
        const prefix = govPrefixes[Math.floor(Math.random() * govPrefixes.length)];
        active_clients.push(generateUsername(prefix));
    }

    // Generate other client types
    for (let i = 0; i < deactivatedCount; i++) {
        const prefix = govPrefixes[Math.floor(Math.random() * govPrefixes.length)];
        deactivate_clients.push(generateUsername(prefix));
    }

    for (let i = 0; i < pausedCount; i++) {
        const prefix = govPrefixes[Math.floor(Math.random() * govPrefixes.length)];
        paused_clients.push(generateUsername(prefix));
    }

    for (let i = 0; i < blockedCount; i++) {
        const prefix = govPrefixes[Math.floor(Math.random() * govPrefixes.length)];
        blocked_clients.push(generateUsername(prefix));
    }

    for (let i = 0; i < errorCount; i++) {
        const prefix = govPrefixes[Math.floor(Math.random() * govPrefixes.length)];
        connecting_internet_error.push(generateUsername(prefix));
    }

    // Return data in the expected format - matching server response structure
    // Server returns an array of objects, each containing one key-value pair
    return {
        server: serverName,
        data: [
            { active_clients },
            { deactivate_clients },
            { paused_clients },
            { blocked_clients },
            { connecting_internet_error }
        ]
    };
}

// Generate data based on specific requested keys (matches server behavior)
function generateServerDataForKeys(serverName, govPrefixes, requestedKeys) {
    const allData = {
        active_clients: [],
        deactivate_clients: [],
        paused_clients: [],
        blocked_clients: [],
        connecting_internet_error: []
    };

    // Generate data for each key type
    const counts = {
        active_clients: Math.floor(Math.random() * 10) + 5,
        deactivate_clients: Math.floor(Math.random() * 5) + 1,
        paused_clients: Math.floor(Math.random() * 3) + 1,
        blocked_clients: Math.floor(Math.random() * 3) + 1,
        connecting_internet_error: Math.floor(Math.random() * 4) + 1
    };

    // Generate clients for each requested key
    requestedKeys.forEach(key => {
        if (allData.hasOwnProperty(key)) {
            const count = counts[key];
            for (let i = 0; i < count; i++) {
                const prefix = govPrefixes[Math.floor(Math.random() * govPrefixes.length)];
                allData[key].push(generateUsername(prefix));
            }
        }
    });

    // Return data in server response format - array of objects with one key each
    const responseData = requestedKeys.map(key => {
        return { [key]: allData[key] || [] };
    });

    return {
        server: serverName,
        data: responseData
    };
}

// Generate data for both servers
const server1Data = generateServerData('server1', ['ci', 'gz', 'ax', 'an', 'lx']);
const server2Data = generateServerData('server2', ['kh', 'mn', 'bh', 'bn', 'dk']);

// Display the generated data
console.log('='.repeat(60));
console.log('🎲 GENERATED REDIS SEED DATA');
console.log('='.repeat(60));

console.log('\n📊 SERVER 1 DATA:');
console.log(JSON.stringify(server1Data, null, 2));

console.log('\n📊 SERVER 2 DATA:');
console.log(JSON.stringify(server2Data, null, 2));

console.log('\n='.repeat(60));
console.log('📋 SUMMARY:');
console.log('='.repeat(60));

function summarizeData(data) {
    const summary = {};
    data.data.forEach(item => {
        const key = Object.keys(item)[0];
        const count = item[key].length;
        summary[key] = count;
    });
    return summary;
}

const server1Summary = summarizeData(server1Data);
const server2Summary = summarizeData(server2Data);

console.log(`Server 1: ${JSON.stringify(server1Summary, null, 2)}`);
console.log(`Server 2: ${JSON.stringify(server2Summary, null, 2)}`);

console.log('\n🚀 TO USE THIS DATA:');
console.log('1. Copy the JSON data above');
console.log('2. Set it as the response for your Redis GET endpoints');
console.log('3. Or use this in your mock server responses');

console.log('\n🔧 EXAMPLE: Generate data for specific keys only:');
const requestedKeys = ["active_clients", "deactivate_clients", "connecting_internet_error"];
const server1Filtered = generateServerDataForKeys('server1', ['ci', 'gz', 'ax'], requestedKeys);
console.log('Filtered Server 1 Response:');
console.log(JSON.stringify(server1Filtered, null, 2));

// Export the data for programmatic use
module.exports = {
    server1Data,
    server2Data,
    generateServerData,
    generateServerDataForKeys,
    generateUsername
};
