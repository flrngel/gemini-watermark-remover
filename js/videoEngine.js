import { calculateAlphaMap } from './alphaMap.js';
import { removeWatermark } from './blendModes.js';

export class VideoWatermarkEngine {
    constructor(bg48, bg96) {
        this.bg48 = bg48;
        this.bg96 = bg96;
        this.alphaMaps = {};
    }

    static async create() {
        const loadImage = (src) => new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => resolve(img);
            img.onerror = reject;
            img.src = src;
        });

        try {
            const [bg48, bg96] = await Promise.all([
                loadImage('./assets/bg_48.png'),
                loadImage('./assets/bg_96.png')
            ]);
            return new VideoWatermarkEngine(bg48, bg96);
        } catch (e) {
            console.error("Failed to load assets. Ensure assets/bg_48.png exists.");
            throw e;
        }
    }

    getWatermarkInfo(width, height) {
        const isLarge = width > 1024 && height > 1024;
        const size = isLarge ? 96 : 48;
        const margin = isLarge ? 64 : 32;
        
        return {
            size,
            x: width - margin - size,
            y: height - margin - size,
            width: size, 
            height: size
        };
    }

    async getAlphaMap(size) {
        if (this.alphaMaps[size]) return this.alphaMaps[size];
        
        const canvas = document.createElement('canvas');
        canvas.width = size; canvas.height = size;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(size === 48 ? this.bg48 : this.bg96, 0, 0);
        
        const map = calculateAlphaMap(ctx.getImageData(0, 0, size, size));
        this.alphaMaps[size] = map;
        return map;
    }

    async processVideo(videoFile, onProgress) {
        return new Promise(async (resolve, reject) => {
            const video = document.createElement('video');
            video.src = URL.createObjectURL(videoFile);
            video.muted = true;
            
            await new Promise((res) => {
                video.onloadedmetadata = res;
            });

            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');

            const config = this.getWatermarkInfo(canvas.width, canvas.height);
            const alphaMap = await this.getAlphaMap(config.size);

            // Create a MediaStream from canvas
            const stream = canvas.captureStream(30); // 30 fps
            
            // Get the original audio track if available
            const audioContext = new AudioContext();
            let audioDestination = null;
            let audioSource = null;
            
            try {
                const originalStream = video.captureStream();
                const audioTracks = originalStream.getAudioTracks();
                if (audioTracks.length > 0) {
                    audioDestination = audioContext.createMediaStreamDestination();
                    audioSource = audioContext.createMediaStreamSource(originalStream);
                    audioSource.connect(audioDestination);
                    audioDestination.stream.getAudioTracks().forEach(track => {
                        stream.addTrack(track);
                    });
                }
            } catch (e) {
                console.log('No audio track available or error capturing audio:', e);
            }

            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'video/webm;codecs=vp9',
                videoBitsPerSecond: 5000000
            });

            const chunks = [];
            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunks.push(e.data);
                }
            };

            mediaRecorder.onstop = () => {
                const blob = new Blob(chunks, { type: 'video/webm' });
                URL.revokeObjectURL(video.src);
                if (audioContext) {
                    audioContext.close();
                }
                resolve({
                    blob,
                    width: video.videoWidth,
                    height: video.videoHeight,
                    duration: video.duration
                });
            };

            mediaRecorder.onerror = (e) => {
                reject(e);
            };

            // Start recording
            mediaRecorder.start();

            // Process frames
            video.play();
            
            const processFrame = async () => {
                if (video.ended || video.paused) {
                    mediaRecorder.stop();
                    return;
                }

                ctx.drawImage(video, 0, 0);
                const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                removeWatermark(imageData, alphaMap, config);
                ctx.putImageData(imageData, 0, 0);

                // Report progress
                if (onProgress) {
                    const progress = (video.currentTime / video.duration) * 100;
                    onProgress(progress);
                }

                requestAnimationFrame(processFrame);
            };

            video.onended = () => {
                setTimeout(() => {
                    mediaRecorder.stop();
                }, 100);
            };

            processFrame();
        });
    }
}
