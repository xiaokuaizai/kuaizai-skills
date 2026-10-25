// 火山引擎 TTS V3 WebSocket 客户端（正确的二进制协议）
// 参考官方文档实现

const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const API_KEY = process.env.VOLC_TTS_API_KEY || process.env.ARK_API_KEY;
const RESOURCE_ID = process.env.VOLC_TTS_RESOURCE_ID || 'seed-tts-2.0';
const ENDPOINT = process.env.VOLC_TTS_ENDPOINT || 'wss://openspeech.bytedance.com/api/v3/tts/bidirection';

// 事件编号
const EVENT_START_CONNECTION = 1;
const EVENT_FINISH_CONNECTION = 3;
const EVENT_START_SESSION = 100;
const EVENT_FINISH_SESSION = 102;
const EVENT_TASK_REQUEST = 200;

// 服务端事件编号
const EVENT_CONNECTION_STARTED = 50;
const EVENT_CONNECTION_FAILED = 51;
const EVENT_SESSION_STARTED = 150;
const EVENT_SESSION_FAILED = 153;
const EVENT_SESSION_FINISHED = 152;
const EVENT_TTS_RESPONSE = 352;

// 音色配置（1.0模型英文音色 - mars/moon/wvae系列）
const VOICE_CONFIG = {
    jiang_che: 'zh_male_M100_conversation_wvae_bigtts',      // Lucas - 美式英语，17岁少年风格
    an_qi: 'en_female_dacey_conversation_wvae_bigtts',       // Daisy - 美式英语女声
    father: 'en_male_sylus_emo_v2_mars_bigtts',              // Sylus - 美式英语，权威感
    mother: 'en_female_skye_emo_v2_mars_bigtts',             // Skye - 美式英语，温暖
    teacher_li: 'en_male_michael_moon_bigtts',               // Michael - 美式英语，理性稳重
    narrator: 'en_male_glen_emo_v2_mars_bigtts'              // Glen - 美式英语，悬疑感
};

// 默认参数（慢语速）
const DEFAULT_PARAMS = {
    format: 'mp3',
    sample_rate: 24000,
    speech_rate: -18
};

// 生成随机session_id
function generateSessionId() {
    return `sess_${Date.now()}_${Math.random().toString(36).substr(2, 12)}`;
}

// 构造二进制请求帧（带session_id）
function buildRequestFrame(eventType, sessionId, payloadJson) {
    const sessionIdStr = sessionId || '';
    const sessionIdBuffer = Buffer.from(sessionIdStr, 'utf8');
    const payloadStr = JSON.stringify(payloadJson || {});
    const payloadBuffer = Buffer.from(payloadStr, 'utf8');

    // Header (4 bytes)
    // Byte 0: version=1, header_size=1 => 0x11
    // Byte 1: message_type=1, flags=4 => 0x14
    // Byte 2: serialization=1 (JSON), compression=0 => 0x10
    // Byte 3: reserved => 0x00
    const header = Buffer.from([0x11, 0x14, 0x10, 0x00]);

    // Event type (4 bytes, int32 big endian)
    const eventBuffer = Buffer.alloc(4);
    eventBuffer.writeInt32BE(eventType, 0);

    // Session ID size (4 bytes, uint32 big endian)
    const sessionIdSizeBuffer = Buffer.alloc(4);
    sessionIdSizeBuffer.writeUInt32BE(sessionIdBuffer.length, 0);

    // Payload size (4 bytes, uint32 big endian)
    const payloadSizeBuffer = Buffer.alloc(4);
    payloadSizeBuffer.writeUInt32BE(payloadBuffer.length, 0);

    return Buffer.concat([header, eventBuffer, sessionIdSizeBuffer, sessionIdBuffer, payloadSizeBuffer, payloadBuffer]);
}

// 构造StartConnection帧（不需要session_id）
function buildStartConnection() {
    // StartConnection不需要session_id，payload为空JSON
    const header = Buffer.from([0x11, 0x14, 0x10, 0x00]);  // Full-client request, with event, JSON
    const eventBuffer = Buffer.alloc(4);
    eventBuffer.writeInt32BE(EVENT_START_CONNECTION, 0);
    const payloadBuffer = Buffer.from('{}', 'utf8');
    const payloadSizeBuffer = Buffer.alloc(4);
    payloadSizeBuffer.writeUInt32BE(payloadBuffer.length, 0);

    return Buffer.concat([header, eventBuffer, payloadSizeBuffer, payloadBuffer]);
}

// 构造StartSession帧（必须带session_id）
function buildStartSession(voiceType, params = {}) {
    const sessionId = generateSessionId();
    const allParams = { ...DEFAULT_PARAMS, ...params };

    // StartSession的payload格式
    const payload = {
        user: { uid: 'user_001' },
        req_params: {
            speaker: voiceType,
            audio_params: {
                format: allParams.format,
                sample_rate: allParams.sample_rate,
                speech_rate: allParams.speech_rate
            }
        }
    };

    return buildRequestFrame(EVENT_START_SESSION, sessionId, payload);
}

// 构造TaskRequest帧（发送文本）
function buildTaskRequest(text, sessionId) {
    const payload = {
        req_params: {
            text: text
        }
    };
    return buildRequestFrame(EVENT_TASK_REQUEST, sessionId, payload);
}

// 构造FinishSession帧
function buildFinishSession(sessionId) {
    return buildRequestFrame(EVENT_FINISH_SESSION, sessionId, {});
}

// 构造FinishConnection帧
function buildFinishConnection() {
    return buildRequestFrame(EVENT_FINISH_CONNECTION, {});
}

// 解析服务端响应
function parseResponse(data) {
    if (data.length < 4) return null;

    const byte0 = data[0];
    const byte1 = data[1];
    const messageType = (byte1 >> 4) & 0x0F;
    const flags = byte1 & 0x0F;
    const serialization = (data[2] >> 4) & 0x0F;

    // Error message (message type = 15, 0b1111)
    // 错误消息没有event number，直接是payload
    if (messageType === 15) {
        // 跳过 header(4)
        let offset = 4;

        // 尝试找到JSON内容
        const jsonStart = data.indexOf('{');
        if (jsonStart >= 0) {
            const jsonStr = data.slice(jsonStart).toString('utf8');
            try {
                return { type: 'error', data: JSON.parse(jsonStr) };
            } catch (e) {
                return { type: 'error', raw: jsonStr };
            }
        }

        return { type: 'error', raw: data.toString('utf8') };
    }

    // 其他响应需要有 event number 和 session_id
    if (data.length < 12) return null;

    const eventType = data.readInt32BE(4);

    // 跳过session_id部分 (session_id_size + session_id)
    let offset = 8;
    const sessionIdSize = data.readUInt32BE(offset);
    offset += 4 + sessionIdSize;  // 4字节size + session_id内容

    // Full-server response (message type = 9, 0b1001)
    if (messageType === 9) {
        if (serialization === 1) {
            if (offset + 4 <= data.length) {
                const jsonSize = data.readUInt32BE(offset);
                offset += 4;

                if (offset + jsonSize <= data.length) {
                    const jsonStr = data.slice(offset, offset + jsonSize).toString('utf8');
                    try {
                        return { type: 'json', eventType, data: JSON.parse(jsonStr || '{}') };
                    } catch (e) {
                        return { type: 'json', eventType, raw: jsonStr };
                    }
                }
            }
            return { type: 'json', eventType, data: {} };
        }
    }

    // Audio-only response (message type = 11, 0b1011)
    if (messageType === 11) {
        // 音频数据在session_id之后
        const audioData = data.slice(offset);
        return { type: 'audio', data: audioData, isLast: flags >= 2 };
    }

    return { type: 'unknown', messageType, flags, eventType, rawLen: data.length };
}

// TTS客户端类
class VolcTTSClient {
    constructor() {
        this.ws = null;
        this.audioBuffer = [];
        this.events = {};
    }

    async connect() {
        return new Promise((resolve, reject) => {
            console.log('正在连接WebSocket...');

            this.ws = new WebSocket(ENDPOINT, {
                headers: {
                    'X-Api-Key': API_KEY,
                    'X-Api-Resource-Id': RESOURCE_ID
                }
            });

            this.ws.binaryType = 'arraybuffer';

            this.ws.on('open', () => {
                console.log('WebSocket连接已建立');
                // 发送StartConnection
                this.ws.send(buildStartConnection());
            });

            this.ws.on('message', (data) => {
                const buf = Buffer.from(data);
                console.log('收到原始数据:', buf.length, 'bytes');
                console.log('前20字节:', buf.slice(0, 20).toString('hex'));

                const response = parseResponse(buf);

                if (response) {
                    console.log('解析结果:', response.type, 'eventType:', response.eventType);

                    if (response.type === 'json') {
                        if (response.eventType === EVENT_CONNECTION_STARTED) {
                            this.events.connectionStarted = true;
                            resolve();
                        } else if (response.eventType === EVENT_SESSION_STARTED) {
                            this.events.sessionStarted = true;
                        } else if (response.eventType === EVENT_SESSION_FINISHED) {
                            this.events.sessionFinished = true;
                        } else if (response.eventType === EVENT_CONNECTION_FAILED) {
                            console.error('连接失败:', response.data);
                            reject(new Error('连接失败'));
                        } else if (response.eventType === EVENT_SESSION_FAILED) {
                            console.error('会话失败:', response.data);
                        } else if (response.raw) {
                            console.log('JSON原始内容:', response.raw.substring(0, 200));
                        }
                    } else if (response.type === 'audio') {
                        this.audioBuffer.push(response.data);
                        if (response.isLast) {
                            this.events.audioComplete = true;
                        }
                    } else if (response.type === 'error') {
                        console.error('协议错误:', response.data);
                    } else if (response.type === 'unknown') {
                        console.log('未知响应类型:', response);
                    }
                }
            });

            this.ws.on('error', (err) => {
                console.error('WebSocket错误:', err);
                reject(err);
            });

            this.ws.on('close', () => {
                console.log('WebSocket连接已关闭');
            });

            // 超时处理
            setTimeout(() => {
                if (!this.events.connectionStarted) {
                    reject(new Error('等待ConnectionStarted超时'));
                }
            }, 5000);
        });
    }

    async synthesize(text, voiceType, outputPath, params = {}) {
        this.audioBuffer = [];
        this.events.sessionStarted = false;
        this.events.sessionFinished = false;
        this.events.audioComplete = false;
        this.currentSessionId = generateSessionId();  // 生成session_id

        return new Promise(async (resolve, reject) => {
            try {
                // 发送StartSession（带session_id）
                const startSessionFrame = buildStartSession(voiceType, params);
                console.log('发送StartSession:', startSessionFrame.length, 'bytes');
                console.log('session_id:', this.currentSessionId);
                this.ws.send(startSessionFrame);

                // 等待SessionStarted
                await this.wait('sessionStarted', 5000);

                // 发送文本任务（带session_id）
                const taskFrame = buildTaskRequest(text, this.currentSessionId);
                console.log('发送TaskRequest:', taskFrame.length, 'bytes');
                this.ws.send(taskFrame);

                // 发送FinishSession（带session_id）
                const finishFrame = buildFinishSession(this.currentSessionId);
                console.log('发送FinishSession:', finishFrame.length, 'bytes');
                this.ws.send(finishFrame);

                // 等待音频完成和SessionFinished
                await this.wait('audioComplete', 30000);
                await this.wait('sessionFinished', 5000);

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

    wait(eventName, timeout) {
        return new Promise((resolve, reject) => {
            const start = Date.now();
            const check = () => {
                if (this.events[eventName]) {
                    resolve();
                } else if (Date.now() - start > timeout) {
                    reject(new Error(`等待${eventName}超时`));
                } else {
                    setTimeout(check, 100);
                }
            };
            check();
        });
    }

    close() {
        if (this.ws) {
            this.ws.send(buildFinishConnection());
            this.ws.close();
        }
    }
}

module.exports = {
    VolcTTSClient,
    VOICE_CONFIG,
    DEFAULT_PARAMS
};
