import { calculateAlphaMap } from './alphaMap.js';
import { removeWatermark } from './blendModes.js';

export class VideoWatermarkEngine {
    constructor(bg48, bg96) {
        this.bg48 = bg48;
        this.bg96 = bg96;
        this.alphaMaps = {};
        // Configuration constants
        this.DEFAULT_VIDEO_BITRATE = 15000000; // 15 Mbps for better quality
        this.FRAME_CAPTURE_BUFFER_MS = 200; // Increased buffer to ensure all frames are captured
        this.DEFAULT_RECORDING_FPS = 30; // Default output video frame rate if detection fails
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

    /**
     * Calculate optimal bitrate based on video resolution
     * Higher resolution videos need higher bitrates to maintain quality
     */
    calculateBitrate(width, height) {
        const pixels = width * height;
        // Base calculation: ~0.1 bits per pixel per frame at 30fps
        // This ensures quality scales with resolution
        let bitrate;
        
        if (pixels <= 921600) { // 720p (1280x720) or lower
            bitrate = 8000000; // 8 Mbps
        } else if (pixels <= 2073600) { // 1080p (1920x1080)
            bitrate = 15000000; // 15 Mbps
        } else if (pixels <= 8294400) { // 4K (3840x2160)
            bitrate = 40000000; // 40 Mbps
        } else {
            bitrate = 60000000; // 60 Mbps for higher resolutions
        }
        
        return bitrate;
    }

    /**
     * Attempt to detect the original video's frame rate
     * Falls back to default if detection fails
     */
    detectFrameRate(video) {
        try {
            // Try to get frame rate from video metadata if available
            // Note: This is not always reliable across all browsers/formats
            if (video.mozParsedFrames !== undefined && video.mozParsedFrames > 0) {
                // Firefox
                const fps = video.mozParsedFrames / video.duration;
                if (fps > 0 && fps <= 120) return Math.round(fps);
            }
            if (video.webkitDecodedFrameCount !== undefined && video.webkitDecodedFrameCount > 0) {
                // Older Chrome/Safari
                const fps = video.webkitDecodedFrameCount / video.duration;
                if (fps > 0 && fps <= 120) return Math.round(fps);
            }
        } catch (e) {
            console.log('Could not detect frame rate:', e);
        }
        
        // Default to 30 FPS for most videos
        return this.DEFAULT_RECORDING_FPS;
    }

    async processVideo(videoFile, onProgress) {
        const video = document.createElement('video');
        const videoUrl = URL.createObjectURL(videoFile);
        video.src = videoUrl;
        video.muted = true;
        video.preload = 'metadata';
        
        try {
            await new Promise((res, rej) => {
                video.onloadedmetadata = res;
                video.onerror = rej;
            });

            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d', { 
                alpha: false,
                desynchronized: false // Ensure synchronous drawing for consistency
            });

            const config = this.getWatermarkInfo(canvas.width, canvas.height);
            const alphaMap = await this.getAlphaMap(config.size);

            // Calculate optimal bitrate and FPS based on video properties
            const bitrate = this.calculateBitrate(canvas.width, canvas.height);
            const fps = this.detectFrameRate(video);
            
            console.log(`Processing video: ${canvas.width}x${canvas.height}, FPS: ${fps}, Bitrate: ${bitrate}`);

            // Create a MediaStream from canvas at detected/optimal FPS
            const stream = canvas.captureStream(fps);
            
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
                // Create MediaRecorder with fallback codec support and optimal settings
                let mediaRecorder;
                const mimeTypes = [
                    'video/webm;codecs=vp9,opus',
                    'video/webm;codecs=vp9',
                    'video/webm;codecs=vp8,opus',
                    'video/webm;codecs=vp8',
                    'video/webm'
                ];
                
                let selectedMimeType = 'video/webm';
                for (const mimeType of mimeTypes) {
                    if (MediaRecorder.isTypeSupported(mimeType)) {
                        selectedMimeType = mimeType;
                        console.log(`Using codec: ${mimeType}`);
                        break;
                    }
                }
                
                mediaRecorder = new MediaRecorder(stream, {
                    mimeType: selectedMimeType,
                    videoBitsPerSecond: bitrate
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

                // Process frames with better synchronization
                video.play();
                
                let lastFrameTime = 0;
                const frameInterval = 1000 / fps; // Target interval between frames in ms
                let recordingStopped = false;
                
                const processFrame = (currentTime) => {
                    if (video.ended || video.paused || recordingStopped) {
                        return;
                    }

                    // Throttle frame processing to match target FPS
                    // This helps prevent processing the same frame multiple times
                    const elapsed = currentTime - lastFrameTime;
                    
                    if (elapsed >= frameInterval - 1) { // Small tolerance
                        lastFrameTime = currentTime;
                        
                        // Draw and process the current frame
                        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                        removeWatermark(imageData, alphaMap, config);
                        ctx.putImageData(imageData, 0, 0);

                        // Report progress
                        if (onProgress && video.duration > 0) {
                            const progress = Math.min((video.currentTime / video.duration) * 100, 100);
                            onProgress(progress);
                        }
                    }

                    requestAnimationFrame(processFrame);
                };

                video.onended = () => {
                    // Give a buffer to ensure all frames are captured
                    // This prevents race conditions where the recorder stops before the last frame
                    setTimeout(() => {
                        if (!recordingStopped && mediaRecorder.state !== 'inactive') {
                            recordingStopped = true;
                            
                            // Process the last frame one more time to ensure it's captured
                            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                            removeWatermark(imageData, alphaMap, config);
                            ctx.putImageData(imageData, 0, 0);
                            
                            // Small additional delay before stopping to ensure last frame is recorded
                            setTimeout(() => {
                                if (mediaRecorder.state !== 'inactive') {
                                    mediaRecorder.stop();
                                }
                            }, 100);
                        }
                    }, this.FRAME_CAPTURE_BUFFER_MS);
                };

                // Start frame processing
                requestAnimationFrame(processFrame);
            });
        } catch (error) {
            // Clean up resources on error
            URL.revokeObjectURL(videoUrl);
            throw error;
        }
    }
}
