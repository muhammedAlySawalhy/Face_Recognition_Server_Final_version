#!/usr/bin/env node

/**
 * Redis Seed Script
 * Seeds Redis with sample data matching the expected structure for the Dashboard
 */

// Import the mock data generator
const { generateServerData } = require('./generate-mock-data.js');

// Try to import Redis, fallback to manual connection if not available
let Redis;
try {
    Redis = require('redis');
} catch (error) {
    console.log('⚠️  Redis package not found. Installing...');
    console.log('Please run: npm install redis --legacy-peer-deps');
    process.exit(1);
}

// Sample data structure that matches what the DashboardContext expects
const sampleData = {
    server1: generateServerData('server1', ['ci', 'gz', 'ax', 'an', 'lx']),
    server2: generateServerData('server2', ['kh', 'mn', 'bh', 'bn', 'dk'])
};

// Redis keys that the application expects
const REDIS_KEYS = [
    "active_clients",
    "deactivate_clients",
    "paused_clients",
    "blocked_clients",
    "connecting_internet_error"
];

async function connectToRedis(config = {}) {
    const defaultConfig = {
        host: 'localhost',
        port: 6379,
        password: undefined,
        ...config
    };

    console.log(`🔌 Connecting to Redis at ${defaultConfig.host}:${defaultConfig.port}...`);

    const client = Redis.createClient({
        socket: {
            host: defaultConfig.host,
            port: defaultConfig.port
        },
        password: defaultConfig.password
    });

    client.on('error', (err) => {
        console.error('❌ Redis Client Error:', err);
    });

    client.on('connect', () => {
        console.log('✅ Connected to Redis');
    });

    await client.connect();
    return client;
}

async function seedRedisWithNewFormat() {
    console.log('🌱 Starting Redis seeding with generated data...');

    let redis1, redis2;

    try {
        // Connect to Redis (you can modify these configs for your setup)
        redis1 = await connectToRedis({ host: 'localhost', port: 6379 });

        // For this example, we'll use the same Redis instance with different keys
        // In production, you might use different databases or different Redis instances
        redis2 = redis1; // Using same client for demo

        console.log('📝 Storing generated data in Redis...');

        // Store Server 1 data
        console.log('\n� Server 1 Data:');
        console.log(JSON.stringify(sampleData.server1, null, 2));
        await redis1.set('server1_data', JSON.stringify(sampleData.server1));
        console.log('✅ Server 1 data stored in Redis key: server1_data');

        // Store Server 2 data  
        console.log('\n� Server 2 Data:');
        console.log(JSON.stringify(sampleData.server2, null, 2));
        await redis2.set('server2_data', JSON.stringify(sampleData.server2));
        console.log('✅ Server 2 data stored in Redis key: server2_data');

        console.log('\n🎉 Redis seeding completed successfully!');

        // Verify the data
        console.log('\n🔍 Verifying stored data...');
        const server1Stored = await redis1.get('server1_data');
        const server2Stored = await redis2.get('server2_data');

        if (server1Stored && server2Stored) {
            console.log('✅ Data verification successful!');

            const server1Data = JSON.parse(server1Stored);
            const server2Data = JSON.parse(server2Stored);

            console.log('\n📈 Summary:');
            console.log(`Server 1: ${server1Data.data.length} data groups`);
            console.log(`Server 2: ${server2Data.data.length} data groups`);

            // Show active clients count
            const server1Active = server1Data.data.find(item => item.active_clients);
            const server2Active = server2Data.data.find(item => item.active_clients);

            console.log(`Server 1 Active Clients: ${server1Active?.active_clients?.length || 0}`);
            console.log(`Server 2 Active Clients: ${server2Active?.active_clients?.length || 0}`);
        } else {
            console.log('❌ Data verification failed!');
        }

    } catch (error) {
        console.error('❌ Error seeding Redis:', error.message);

        if (error.code === 'ECONNREFUSED') {
            console.log('\n💡 Troubleshooting:');
            console.log('1. Make sure Redis is running on your system');
            console.log('2. Install Redis: https://redis.io/docs/getting-started/installation/');
            console.log('3. Start Redis server: redis-server');
            console.log('4. Or use Docker: docker run -d -p 6379:6379 redis');
        }
    } finally {
        // Close connections
        if (redis1) {
            await redis1.quit();
            console.log('🔌 Redis connections closed');
        }
    }
}

// Alternative function to just show the data without Redis
function showGeneratedData() {
    console.log('🎲 Generated Data (without Redis connection):');
    console.log('='.repeat(60));

    console.log('\n� SERVER 1 DATA:');
    console.log(JSON.stringify(sampleData.server1, null, 2));

    console.log('\n� SERVER 2 DATA:');
    console.log(JSON.stringify(sampleData.server2, null, 2));

    console.log('\n💡 To use this data:');
    console.log('1. Start Redis server');
    console.log('2. Run this script again to store in Redis');
    console.log('3. Or copy this JSON for manual testing');
}

// Main execution
const mode = process.argv[2];

if (mode === 'show') {
    showGeneratedData();
} else {
    seedRedisWithNewFormat().catch(() => {
        console.log('\n⚠️  Failed to connect to Redis. Showing generated data instead:');
        showGeneratedData();
    });
}

// Export for use in other scripts
module.exports = {
    seedRedisWithNewFormat,
    showGeneratedData,
    sampleData,
    connectToRedis
};
