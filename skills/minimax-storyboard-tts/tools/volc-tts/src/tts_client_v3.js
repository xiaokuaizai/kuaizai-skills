// 火山引擎 TTS V3 WebSocket 客户端
// 使用二进制协议格式

const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

// 加载环境变量
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const API_KEY = process.env.VOLC_TTS_API_KEY || process.env.ARK_API_KEY;
const RESOURCE_ID = process.env.VOLC_TTS_RESOURCE_ID || 'seed-tts-2.0';
const ENDPOINT = process.env.VOLC_TTS_ENDPOINT || 'wss://openspeech.bytedance.com/api/v3/tts/bidirection';

// 音色配置（英文音色优先）
const VOICE_CONFIG = {
    jiang_che: 'zh_male_shaonianzixin_uranus_bigtts',      // 少年梓辛/Brayan - 支持英文
    an_qi: 'zh_female_cancan_uranus_bigtts',               // 知性灿灿 - 支持英文
    father: 'zh_male_ruyayichen_uranus_bigtts',            // 儒雅逸辰
    mother: 'zh_female_wenroumama_uranus_bigtts',          // 温柔妈妈
    teacher_li: 'zh_male_jieshuoxiaoming_uranus_bigtts',   // 解说小明
    narrator: 'zh_male_xuanyijieshuo_uranus_bigtts'        // 悬疑解说
};

// 默认TTS参数（慢语速）
const DEFAULT_PARAMS = {
    format: 'mp3',
    sample_rate: 24000,
    speech_rate: -18
};

// 生成请求ID
function generateRequestId() {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// 构造二进制协议头部
function buildBinaryHeader(messageType, messageTypeFlags, serialization, compression) {
    // Byte 0: Protocol version (4 bits) + Header size (4 bits)
    // Protocol version = 1, Header size = 1 (4 bytes)
    const byte0 = (1 << 4) | 1;

    // Byte 1: Message type (4 bits) + Message type specific flags (4 bits)
    const byte1 = (messageType << 4) | messageTypeFlags;

    // Byte 2: Serialization method (4 bits) + Compression method (4 bits)
    const byte2 = (serialization << 4) | compression;

    // Byte 3: Reserved (0x00)
    const byte3 = 0x00;

    return Buffer.from([byte0, byte1, byte2, byte3]);
}

// 构造StartConnection请求
function buildStartConnection() {
    const payload = JSON.stringify({
        type: 'StartConnection',
        version: '3.1',
        request_id: generateRequestId()
    });

    const payloadBuffer = Buffer.from(payload, 'utf8');
    const header = buildBinaryHeader(1, 0, 1, 0);  // Full client request, JSON, no compression

    // Payload size (4 bytes, big endian)
    const payloadSizeBuffer = Buffer.alloc(4);
    payloadSizeBuffer.writeUInt32BE(payloadBuffer.length, 0);

    return Buffer.concat([header, payloadSizeBuffer, payloadBuffer]);
}

// 构造StartSession请求
function buildStartSession(voiceType, params = {}) {
    const allParams = { ...DEFAULT_PARAMS, ...params };

    const payload = JSON.stringify({
        type: 'StartSession',
        request_id: generateRequestId(),
        payload: {
            speaker: voiceType,
            ...allParams
        }
    });

    const payloadBuffer = Buffer.from(payload, 'utf8');
    const header = buildBinaryHeader(1, 0, 1, 0);

    const payloadSizeBuffer = Buffer.alloc(4);
    payloadSizeBuffer.writeUInt32BE(payloadBuffer.length, 0);

    return Buffer.concat([header, payloadSizeBuffer, payloadBuffer]);
}

// 构造TaskRequest（发送文本）
function buildTaskRequest(text, params = {}) {
    const allParams = { ...DEFAULT_PARAMS, ...params };

    const payload = JSON.stringify({
        type: 'TaskRequest',
        request_id: generateRequestId(),
        payload: {
            text: text,
            ...allParams
        }
    });

    const payloadBuffer = Buffer.from(payload, 'utf8');
    const header = buildBinaryHeader(1, 0, 1, 0);

    const payloadSizeBuffer = Buffer.alloc(4);
    payloadSizeBuffer.writeUInt32BE(payloadBuffer.length, 0);

    return Buffer.concat([header, payloadSizeBuffer, payloadBuffer]);
}

// 构造FinishSession请求
function buildFinishSession() {
    const payload = JSON.stringify({
        type: 'FinishSession',
        request_id: generateRequestId()
    });

    const payloadBuffer = Buffer.from(payload, 'utf8');
    const header = buildBinaryHeader(1, 0, 1, 0);

    const payloadSizeBuffer = Buffer.alloc(4);
    payloadSizeBuffer.writeUInt32BE(payloadBuffer.length, 0);

    return Buffer.concat([header, payloadSizeBuffer, payloadBuffer]);
}

// 构造FinishConnection请求
function buildFinishConnection() {
    const payload = JSON.stringify({
        type: 'FinishConnection',
        request_id: generateRequestId()
    });

    const payloadBuffer = Buffer.from(payload, 'utf8');
    const header = buildBinaryHeader(1, 0, 1, 0);

    const payloadSizeBuffer = Buffer.alloc(4);
    payloadSizeBuffer.writeUInt32BE(payloadBuffer.length, 0);

    return Buffer.concat([header, payloadSizeBuffer, payloadBuffer]);
}

// 解析二进制响应
function parseBinaryResponse(data) {
    if (data.length < 4) {
        return null;
    }

    const byte0 = data[0];
    const byte1 = data[1];
    const byte2 = data[2];

    const protocolVersion = (byte0 >> 4) & 0x0F;
    const headerSize = (byte0 & 0x0F) * 4;
    const messageType = (byte1 >> 4) & 0x0F;
    const messageFlags = byte1 & 0x0F;
    const serialization = (byte2 >> 4) & 0x0F;
    const compression = byte2 & 0x0F;

    // Audio-only response (message type = 11, 0b1011)
    if (messageType === 0b1011) {
        // 纯音频数据，没有序列化
        const audioData = data.slice(headerSize);
        return {
            type: 'audio',
            data: audioData,
            isLast: messageFlags >= 2  // flags >= 2 表示最后一包
        };
    }

    // Error message (message type = 15, 0b1111)
    if (messageType === 0b1111) {
        const payloadSize = data.readUInt32BE(headerSize);
        const payload = data.slice(headerSize + 4, headerSize + 4 + payloadSize);
        return {
            type: 'error',
            data: JSON.parse(payload.toString('utf8'))
        };
    }

    // JSON response (serialization = 1)
    if (serialization === 1) {
        const payloadSize = data.readUInt32BE(headerSize);
        const payload = data.slice(headerSize + 4, headerSize + 4 + payloadSize);
        return {
            type: 'json',
            data: JSON.parse(payload.toString('utf8'))
        };
    }

    return null;
}

// TTS客户端类
class VolcTTSClientV3 {
    constructor() {
        this.ws = null;
        this.audioBuffer = [];
        this.isConnected = false;
        this.sessionStarted = false;
        this.sessionFinished = false;
    }

    async connect() {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(ENDPOINT, {
                headers: {
                    'X-Api-Key': API_KEY,
                    'X-Api-Resource-Id': RESOURCE_ID
                }
            });

            this.ws.on('open', () => {
                console.log('WebSocket连接已建立');
                this.isConnected = true;

                // 发送StartConnection
                this.ws.send(buildStartConnection());
            });

            this.ws.on('message', (data) => {
                const response = parseBinaryResponse(data);

                if (response) {
                    if (response.type === 'json') {
                        const jsonData = response.data;
                        console.log('收到JSON响应:', jsonData.type);

                        if (jsonData.type === 'ConnectionStarted') {
                            this.connectionStarted = true;
                        } else if (jsonData.type === 'SessionStarted') {
                            this.sessionStarted = true;
                        } else if (jsonData.type === 'SessionFinished') {
                            this.sessionFinished = true;
                        } else if (jsonData.type === 'Error') {
                            console.error('TTS错误:', jsonData);
                        }
                    } else if (response.type === 'audio') {
                        this.audioBuffer.push(response.data);
                        if (response.isLast) {
                            this.audioComplete = true;
                        }
                    } else if (response.type === 'error') {
                        console.error('协议错误:', response.data);
                    }
                }
            });

            this.ws.on('error', (err) => {
                console.error('WebSocket错误:', err);
                reject(err);
            });

            this.ws.on('close', () => {
                console.log('WebSocket连接已关闭');
                this.isConnected = false;
            });

            // 等待ConnectionStarted
            setTimeout(() => {
                if (this.connectionStarted) {
                    resolve();
                } else {
                    reject(new Error('等待ConnectionStarted超时'));
                }
            }, 5000);
        });
    }

    async synthesize(text, voiceType, outputPath, params = {}) {
        this.audioBuffer = [];
        this.sessionStarted = false;
        this.sessionFinished = false;
        this.audioComplete = false;

        return new Promise(async (resolve, reject) => {
            try {
                // 发送StartSession
                this.ws.send(buildStartSession(voiceType, params));

                // 等待SessionStarted
                await this.waitForCondition(() => this.sessionStarted, 5000, 'SessionStarted');

                // 发送文本任务
                this.ws.send(buildTaskRequest(text, params));

                // 发送FinishSession
                this.ws.send(buildFinishSession());

                // 等待音频收集完成
                await this.waitForCondition(() => this.audioComplete || this.sessionFinished, 30000, '音频生成');

                // 保存音频
                if (this.audioBuffer.length > 0) {
                    const audioData = Buffer.concat(this.audioBuffer);
                    fs.writeFileSync(outputPath, audioData);
                    console.log(`音频已保存: ${outputPath} (${audioData.length} bytes)`);
                    resolve(outputPath);
                } else {
                    reject(new Error('没有收到音频数据'));
                }
            } catch (err) {
                reject(err);
            }
        });
    }

    waitForCondition(conditionFn, timeout, name) {
        return new Promise((resolve, reject) => {
            const startTime = Date.now();
            const checkInterval = 100;

            const check = () => {
                if (conditionFn()) {
                    resolve();
                } else if (Date.now() - startTime > timeout) {
                    reject(new Error(`等待${name}超时`));
                } else {
                    setTimeout(check, checkInterval);
                }
            };

            check();
        });
    }

    close() {
        if (this.ws && this.isConnected) {
            this.ws.send(buildFinishConnection());
            this.ws.close();
        }
    }
}

module.exports = {
    VolcTTSClientV3,
    VOICE_CONFIG,
    DEFAULT_PARAMS
};
