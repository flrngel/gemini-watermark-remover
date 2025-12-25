import { calculateAlphaMap } from './alphaMap.js';
import { removeWatermark } from './blendModes.js';

export class VideoWatermarkEngine {
    constructor(bg48, bg96) {
        this.bg48 = bg48;
        this.bg96 = bg96;
        this.alphaMaps = {};
        // Configuration constants
        this.DEFAULT_VIDEO_BITRATE = 5000000; // 5 Mbps
        this.FRAME_CAPTURE_BUFFER_MS = 100; // Buffer to ensure all frames are captured
        this.RECORDING_FPS = 30; // Output video frame rate
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
            console.error("Failed to load assets. Ensure assets/bg_48.png and assets/bg_96.png exist.");
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
        const video = document.createElement('video');
        const videoUrl = URL.createObjectURL(videoFile);
        video.src = videoUrl;
        video.muted = true;
        
        try {
            await new Promise((res) => {
                video.onloadedmetadata = res;
            });

            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');

            const config = this.getWatermarkInfo(canvas.width, canvas.height);
            const alphaMap = await this.getAlphaMap(config.size);

            // Create a MediaStream from canvas at specified FPS
            const stream = canvas.captureStream(this.RECORDING_FPS);
            
            // Get the original audio track if available
            let audioContext = null;
            let audioDestination = null;
            let audioSource = null;
            
            try {
                const originalStream = video.captureStream();
                const audioTracks = originalStream.getAudioTracks();
                if (audioTracks.length > 0) {
                    audioContext = new AudioContext();
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

            return new Promise((resolve, reject) => {
                // Create MediaRecorder with fallback codec support
                let mediaRecorder;
                const mimeTypes = [
                    'video/webm;codecs=vp9',
                    'video/webm;codecs=vp8',
                    'video/webm'
                ];
                
                let selectedMimeType = 'video/webm';
                for (const mimeType of mimeTypes) {
                    if (MediaRecorder.isTypeSupported(mimeType)) {
                        selectedMimeType = mimeType;
                        break;
                    }
                }
                
                mediaRecorder = new MediaRecorder(stream, {
                    mimeType: selectedMimeType,
                    videoBitsPerSecond: this.DEFAULT_VIDEO_BITRATE
                });

                const chunks = [];
                mediaRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0) {
                        chunks.push(e.data);
                    }
                };

                mediaRecorder.onstop = () => {
                    const blob = new Blob(chunks, { type: selectedMimeType });
                    URL.revokeObjectURL(videoUrl);
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
                    URL.revokeObjectURL(videoUrl);
                    if (audioContext) {
                        audioContext.close();
                    }
                    reject(e);
                };

                // Start recording
                mediaRecorder.start();

                // Process frames
                video.play();
                
                // Process each frame as it's drawn to the canvas
                // Frames are processed at browser refresh rate (~60fps) using requestAnimationFrame
                // but the MediaRecorder captures and encodes them at the configured RECORDING_FPS
                const processFrame = async () => {
                    if (video.ended || video.paused) {
                        // Don't stop here - let onended handler manage the stop with buffer time
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
                    // Give a small buffer to ensure all frames are captured
                    // This prevents race conditions where the recorder stops before the last frame
                    setTimeout(() => {
                        if (mediaRecorder.state !== 'inactive') {
                            mediaRecorder.stop();
                        }
                    }, this.FRAME_CAPTURE_BUFFER_MS);
                };

                processFrame();
            });
        } catch (error) {
            // Clean up resources on error
            URL.revokeObjectURL(videoUrl);
            throw error;
        }
    }
}
