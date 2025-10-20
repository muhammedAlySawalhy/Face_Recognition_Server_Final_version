#!/usr/bin/env node

/**
 * Redis Data Viewer
 * Retrieves and displays data from Redis
 */

// Try to import Redis
let Redis;
try {
    Redis = require('redis');
} catch (error) {
    console.log('⚠️  Redis package not found. Please install: npm install redis --legacy-peer-deps');
    process.exit(1);
}

async function viewRedisData() {
    console.log('👀 Retrieving data from Redis...');

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

        // Get Server 1 data
        console.log('\n📊 SERVER 1 DATA FROM REDIS:');
        const server1Data = await client.get('server1_data');
        if (server1Data) {
            const parsed1 = JSON.parse(server1Data);
            console.log(JSON.stringify(parsed1, null, 2));

            // Show summary
            const active1 = parsed1.data.find(item => item.active_clients);
            console.log(`\n📈 Server 1 Summary: ${active1?.active_clients?.length || 0} active clients`);
        } else {
            console.log('❌ No data found for server1_data');
        }

        // Get Server 2 data
        console.log('\n📊 SERVER 2 DATA FROM REDIS:');
        const server2Data = await client.get('server2_data');
        if (server2Data) {
            const parsed2 = JSON.parse(server2Data);
            console.log(JSON.stringify(parsed2, null, 2));

            // Show summary
            const active2 = parsed2.data.find(item => item.active_clients);
            console.log(`\n📈 Server 2 Summary: ${active2?.active_clients?.length || 0} active clients`);
        } else {
            console.log('❌ No data found for server2_data');
        }

        // List all keys
        console.log('\n🔑 ALL REDIS KEYS:');
        const keys = await client.keys('*');
        console.log(keys);

    } catch (error) {
        console.error('❌ Error connecting to Redis:', error.message);

        if (error.code === 'ECONNREFUSED') {
            console.log('\n💡 Make sure Redis server is running!');
            console.log('Start Redis: redis-server');
            console.log('Or with Docker: docker run -d -p 6379:6379 redis');
        }
    } finally {
        if (client) {
            await client.quit();
            console.log('\n🔌 Redis connection closed');
        }
    }
}

// Run the viewer
viewRedisData();
