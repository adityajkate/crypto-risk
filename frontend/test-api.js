const API_BASE_URL = process.env.VITE_API_URL || 'http://localhost:8000';

async function testApi() {
  try {
    console.log(`Testing API at: ${API_BASE_URL}`);
    const response = await fetch(`${API_BASE_URL}/api/v1/coin/bitcoin/price`);
    const result = await response.json();
    console.log('Full response:', JSON.stringify(result, null, 2));
    console.log('\nData field:', JSON.stringify(result.data, null, 2));
    console.log('\nCurrent price:', result.data.current_price);
  } catch (error) {
    console.error('Error:', error);
  }
}

testApi();
