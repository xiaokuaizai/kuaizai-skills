// 生成音色自我介绍语音样本
// 用于用户确认音色选择

const { VolcTTSClient, VOICE_CONFIG, DEFAULT_PARAMS } = require('./tts_client');
const fs = require('fs');
const path = require('path');

// 自我介绍文本（英文台词）
const SAMPLE_TEXTS = {
    jiang_che: "Unless decoded, the plan fails. This is not ordinary noise.",
    an_qi: "I will join. Do not investigate this alone.",
    father: "That is not a joke. It is a test signal we left ten years ago.",
    mother: "Record everything first. Do not explain it too soon.",
    teacher_li: "From the frequency, structure, and coordinate logic, it looks like a scientific test signal.",
    narrator: "At 2:17 a.m., the old radio in the garage suddenly came alive."
};

// 输出目录
const OUTPUT_DIR = path.join(__dirname, '..', 'output', 'samples');

// 确保输出目录存在
if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// 生成所有样本
async function generateAllSamples() {
    console.log('开始生成音色自我介绍语音样本...\n');
    console.log('使用的音色:');
    for (const [role, voice] of Object.entries(VOICE_CONFIG)) {
        console.log(`  ${role}: ${voice}`);
    }
    console.log('');

    const client = new VolcTTSClient();

    try {
        await client.connect();
        console.log('连接成功！\n');

        for (const [role, text] of Object.entries(SAMPLE_TEXTS)) {
            const voiceType = VOICE_CONFIG[role];
            const outputPath = path.join(OUTPUT_DIR, `${role}_sample.mp3`);

            console.log(`[${role}] "${text}"`);

            try {
                await client.synthesize(text, voiceType, outputPath, { speech_rate: -18 });
                console.log(`  ✓ 已保存\n`);
            } catch (err) {
                console.log(`  ✗ 失败: ${err.message}\n`);
            }
        }

        client.close();
        console.log('全部完成！');
        console.log(`输出目录: ${OUTPUT_DIR}`);

    } catch (err) {
        console.error('失败:', err.message);
        client.close();
    }
}

// 生成单个样本
async function generateSingleSample(role) {
    if (!SAMPLE_TEXTS[role]) {
        console.error(`未知角色: ${role}`);
        console.log('可用角色:', Object.keys(SAMPLE_TEXTS).join(', '));
        return;
    }

    const client = new VolcTTSClient();
    const outputPath = path.join(OUTPUT_DIR, `${role}_sample.mp3`);

    try {
        await client.connect();
        await client.synthesize(SAMPLE_TEXTS[role], VOICE_CONFIG[role], outputPath);
        console.log(`已生成: ${outputPath}`);
        client.close();
    } catch (err) {
        console.error('失败:', err.message);
        client.close();
    }
}

// 运行
const args = process.argv.slice(2);
if (args.length > 0) {
    generateSingleSample(args[0]);
} else {
    generateAllSamples();
}