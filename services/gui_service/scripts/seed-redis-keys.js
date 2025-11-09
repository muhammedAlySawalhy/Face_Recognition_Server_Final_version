#!/usr/bin/env node

/**
 * Redis Seed Script for Key-Based Server Responses
 * Simulates the exact server behavior where keys are requested and specific data is returned
 */

const { generateServerDataForKeys } = require('./generate-mock-data.js');

// Try to import Redis
let Redis;
try {
    Redis = require('redis');
} catch (error) {
    console.log('⚠️  Redis package not found. Please install: npm install redis --legacy-peer-deps');
    process.exit(1);
}

// The keys that your DashboardContext requests
const REQUESTED_KEYS = [
    "active_clients",
    "deactivate_clients",
    "paused_clients",
    "blocked_clients",
    "connecting_internet_error"
];

async function seedRedisWithKeyBasedData() {
    console.log('🌱 Seeding Redis with key-based server response data...');

    let client;

    try {
        // Connect to Redis
        client = Redis.createClient({
            socket: {
                host: 'localhost',
                port: 6379
            }
        });

        await client.connect();
        console.log('✅ Connected to Redis');

        // Generate realistic server responses for both servers
        const server1Response = generateServerDataForKeys('server1', ['ci', 'gz', 'ax', 'an', 'lx'], REQUESTED_KEYS);
        const server2Response = generateServerDataForKeys('server2', ['kh', 'mn', 'bh', 'bn', 'dk'], REQUESTED_KEYS);

        console.log('\n📊 Generated Server 1 Response:');
        console.log(JSON.stringify(server1Response, null, 2));

        console.log('\n📊 Generated Server 2 Response:');
        console.log(JSON.stringify(server2Response, null, 2));

        // Store the responses in Redis
        await client.set('server1_response', JSON.stringify(server1Response));
        await client.set('server2_response', JSON.stringify(server2Response));

        console.log('\n✅ Stored server responses in Redis');
        console.log('   📦 server1_response - Server 1 key-based data');
        console.log('   📦 server2_response - Server 2 key-based data');

        // Also store individual key data for testing
        for (const key of REQUESTED_KEYS) {
            const server1KeyData = server1Response.data.find(item => item[key]);
            const server2KeyData = server2Response.data.find(item => item[key]);

            if (server1KeyData) {
                await client.set(`server1:${key}`, JSON.stringify(server1KeyData[key]));
            }
            if (server2KeyData) {
                await client.set(`server2:${key}`, JSON.stringify(server2KeyData[key]));
            }
        }

        console.log('\n✅ Stored individual key data for testing');

        // Verify the stored data
        console.log('\n🔍 Verification:');
        const storedServer1 = await client.get('server1_response');
        const storedServer2 = await client.get('server2_response');

        if (storedServer1 && storedServer2) {
            const s1 = JSON.parse(storedServer1);
            const s2 = JSON.parse(storedServer2);

            const s1Active = s1.data.find(item => item.active_clients);
            const s2Active = s2.data.find(item => item.active_clients);

            console.log(`✅ Server 1: ${s1Active?.active_clients?.length || 0} active clients`);
            console.log(`✅ Server 2: ${s2Active?.active_clients?.length || 0} active clients`);
            console.log(`✅ Both servers have ${s1.data.length} key groups each`);
        }

        // Show all Redis keys
        console.log('\n🔑 All Redis Keys:');
        const allKeys = await client.keys('*');
        const ourKeys = allKeys.filter(key => key.startsWith('server'));
        console.log(ourKeys);

    } catch (error) {
        console.error('❌ Error:', error.message);

        if (error.code === 'ECONNREFUSED') {
            console.log('\n💡 Redis server not running. Start with:');
            console.log('   redis-server');
            console.log('   # or with Docker:');
            console.log('   docker run -d -p 6379:6379 redis');
        }
    } finally {
        if (client) {
            await client.quit();
            console.log('\n🔌 Redis connection closed');
        }
    }
}

// Function to simulate server endpoint behavior
function simulateServerEndpoint(serverName, requestedKeys) {
    console.log(`\n🖥️  Simulating ${serverName} endpoint with keys:`, requestedKeys);

    const govPrefixes = serverName === 'server1' ?
        ['ci', 'gz', 'ax', 'an', 'lx'] :
        ['kh', 'mn', 'bh', 'bn', 'dk'];

    const response = generateServerDataForKeys(serverName, govPrefixes, requestedKeys);

    console.log('📤 Server Response:');
    console.log(JSON.stringify(response, null, 2));

    return response;
}

// Main execution
const mode = process.argv[2];

if (mode === 'simulate') {
    // Simulate the exact server behavior
    console.log('🎭 Simulating Server Endpoint Behavior');
    console.log('='.repeat(50));

    simulateServerEndpoint('server1', REQUESTED_KEYS);
    simulateServerEndpoint('server2', REQUESTED_KEYS);

    console.log('\n📝 This simulates your FastAPI endpoints:');
    console.log('POST /redis/get with body: {"keys": ["active_clients", "deactivate_clients", ...]}');

} else {
    // Seed Redis with the data
    seedRedisWithKeyBasedData().catch(() => {
        console.log('\n⚠️  Failed to connect to Redis. Showing simulation instead:');
        simulateServerEndpoint('server1', REQUESTED_KEYS);
        simulateServerEndpoint('server2', REQUESTED_KEYS);
    });
}

module.exports = {
    seedRedisWithKeyBasedData,
    simulateServerEndpoint,
    REQUESTED_KEYS
};
