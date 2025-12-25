import { WatermarkEngine } from './engine.js';
import { VideoWatermarkEngine } from './videoEngine.js';

document.addEventListener('DOMContentLoaded', async () => {
    // UI Elements
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const previewSection = document.getElementById('previewSection');
    
    // Images
    const originalImage = document.getElementById('originalImage');
    const processedImage = document.getElementById('processedImage');
    
    // Videos
    const originalVideo = document.getElementById('originalVideo');
    const processedVideo = document.getElementById('processedVideo');
    
    // Metadata Fields
    const originalSize = document.getElementById('originalSize');
    const resultSize = document.getElementById('resultSize');
    const resultStatus = document.getElementById('resultStatus');
    
    // Buttons & Overlay
    const downloadBtn = document.getElementById('downloadBtn');
    const resetBtn = document.getElementById('resetBtn');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingText');
    const progressBar = document.getElementById('progressBar');

    let engine = null;
    let videoEngine = null;
    let isVideoMode = false;

    // --- Init ---
    try {
        engine = await WatermarkEngine.create();
        videoEngine = await VideoWatermarkEngine.create();
    } catch (e) {
        alert("Error: Could not load background assets. Please ensure 'assets/bg_48.png' and 'assets/bg_96.png' exist.");
    }

    // --- Event Listeners ---
    uploadArea.addEventListener('click', () => fileInput.click());
    
    // Drag & Drop Logic
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });

    uploadArea.addEventListener('dragover', () => uploadArea.classList.add('border-gemini-blue', 'bg-blue-50'));
    uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('border-gemini-blue', 'bg-blue-50'));
    
    uploadArea.addEventListener('drop', (e) => {
        uploadArea.classList.remove('border-gemini-blue', 'bg-blue-50');
        handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

    resetBtn.addEventListener('click', () => {
        previewSection.classList.add('hidden');
        uploadArea.classList.remove('hidden');
        fileInput.value = '';
        originalImage.src = '';
        processedImage.src = '';
        if (originalVideo) originalVideo.src = '';
        if (processedVideo) processedVideo.src = '';
        
        // Hide video elements and show image elements
        if (isVideoMode) {
            document.getElementById('originalImageContainer')?.classList.remove('hidden');
            document.getElementById('processedImageContainer')?.classList.remove('hidden');
            document.getElementById('originalVideoContainer')?.classList.add('hidden');
            document.getElementById('processedVideoContainer')?.classList.add('hidden');
            isVideoMode = false;
        }
    });

    // --- Processing Logic ---
    async function handleFiles(files) {
        if (!files.length) return;
        const file = files[0];
        
        const isVideo = file.type.match('video.*');
        const isImage = file.type.match('image.*');
        
        if (!isVideo && !isImage) {
            alert("Please upload a valid image (PNG, JPG, WebP) or video (MP4, WebM)");
            return;
        }

        loadingOverlay.classList.remove('hidden');
        loadingOverlay.classList.add('flex');
        
        if (loadingText) {
            loadingText.textContent = isVideo ? 'Processing video...' : 'Processing image...';
        }
        
        // Reset progress bar
        if (progressBar) {
            progressBar.style.width = '0%';
        }

        try {
            if (isVideo) {
                await handleVideoFile(file);
            } else {
                await handleImageFile(file);
            }
        } catch (error) {
            console.error(error);
            alert(`An error occurred during processing: ${error.message || error}`);
        } finally {
            loadingOverlay.classList.add('hidden');
            loadingOverlay.classList.remove('flex');
        }
    }
    
    async function handleImageFile(file) {
        if (!engine) engine = await WatermarkEngine.create();
        
        const result = await engine.process(file);
        
        // Hide video elements, show image elements
        isVideoMode = false;
        document.getElementById('originalImageContainer')?.classList.remove('hidden');
        document.getElementById('processedImageContainer')?.classList.remove('hidden');
        document.getElementById('originalVideoContainer')?.classList.add('hidden');
        document.getElementById('processedVideoContainer')?.classList.add('hidden');
        
        // 1. Update Images
        originalImage.src = result.originalSrc;
        const processedUrl = URL.createObjectURL(result.blob);
        processedImage.src = processedUrl;
        
        // 2. Update Metadata (Top Right Corner)
        const sizeText = `${result.width} × ${result.height} px`;
        originalSize.textContent = sizeText;
        resultSize.textContent = sizeText;
        resultStatus.textContent = "Watermark Removed"; // Set status text
        
        // 3. Setup Download
        downloadBtn.onclick = () => {
            const a = document.createElement('a');
            a.href = processedUrl;
            a.download = `clean_${file.name.replace(/\.[^/.]+$/, "")}.png`;
            a.click();
        };

        // 4. Show Results
        uploadArea.classList.add('hidden');
        previewSection.classList.remove('hidden');
    }
    
    async function handleVideoFile(file) {
        if (!videoEngine) videoEngine = await VideoWatermarkEngine.create();
        
        const onProgress = (progress) => {
            if (progressBar) {
                progressBar.style.width = `${progress}%`;
            }
            if (loadingText) {
                loadingText.textContent = `Processing video... ${Math.round(progress)}%`;
            }
        };
        
        const result = await videoEngine.processVideo(file, onProgress);
        
        // Hide image elements, show video elements
        isVideoMode = true;
        document.getElementById('originalImageContainer')?.classList.add('hidden');
        document.getElementById('processedImageContainer')?.classList.add('hidden');
        document.getElementById('originalVideoContainer')?.classList.remove('hidden');
        document.getElementById('processedVideoContainer')?.classList.remove('hidden');
        
        // 1. Update Videos
        const originalUrl = URL.createObjectURL(file);
        const processedUrl = URL.createObjectURL(result.blob);
        originalVideo.src = originalUrl;
        processedVideo.src = processedUrl;
        
        // 2. Update Metadata
        const sizeText = `${result.width} × ${result.height} px`;
        const durationText = `${Math.round(result.duration)}s`;
        originalSize.textContent = `${sizeText} • ${durationText}`;
        resultSize.textContent = `${sizeText} • ${durationText}`;
        resultStatus.textContent = "Watermark Removed";
        
        // 3. Setup Download
        downloadBtn.onclick = () => {
            const a = document.createElement('a');
            a.href = processedUrl;
            a.download = `clean_${file.name.replace(/\.[^/.]+$/, "")}.webm`;
            a.click();
        };

        // 4. Show Results
        uploadArea.classList.add('hidden');
        previewSection.classList.remove('hidden');
    }
});