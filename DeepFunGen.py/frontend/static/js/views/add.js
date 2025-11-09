import Api from '../api.js';
import { State } from '../state.js';
import { showToast } from '../app.js';
import I18n from '../i18n.js';
import Native from '../native.js';

const VIDEO_EXTENSIONS = new Set(['.mp4', '.mov', '.m4v', '.avi', '.mkv', '.mpg', '.mpeg', '.wmv']);
const PATH_SPLIT_REGEX = /[\/]/;

const staged = new Map();
let stagedList;
let modelSelect;
let modelFilterToggle;
let addButton;
let browseFilesButton;
let dropZone;
let manualPathInput;
let manualPathButton;
let htmlFileInput;
let recommendButton;

const optionInputs = {};
const trackedInputs = new WeakSet();
let modelFilterVrOnly = false;
let recommendedValues = {};

const DEFAULT_OPTIONS = {
    smooth: 3,
    prominence: 0.1,
    minProminence: 0.0,
    maxSlope: 10.0,
    boostSlope: 7.0,
    minSlope: 0.0,
    merge: 120.0,
    fftDenoise: true,
    fftFrames: 10,
};

function normaliseKey(path) {
    return path.trim().replace(/\\/g, '/').toLowerCase();
}

function stageMetadata(path) {
    const normalised = path.replace(/\\/g, '/');
    const trimmed = normalised.replace(/\/+$/, '');
    const name = trimmed.split(PATH_SPLIT_REGEX).pop() || trimmed || path;
    return { key: normaliseKey(path), path, name };
}

function markDirty(input) {
    if (!input || trackedInputs.has(input)) return;
    trackedInputs.add(input);
}

function bindDirtyTracker(input) {
    if (!input || input.dataset?.dirtyTrackerBound) {
        return;
    }
    const handler = () => markDirty(input);
    const events = input.tagName === 'SELECT'
        ? ['change']
        : input.type === 'checkbox'
            ? ['change']
            : ['input', 'change'];
    events.forEach((event) => input.addEventListener(event, handler));
    input.dataset.dirtyTrackerBound = '1';
}

function registerOptionInput(key, elementId) {
    if (optionInputs[key]) {
        return optionInputs[key];
    }
    const element = document.getElementById(elementId);
    if (element) {
        optionInputs[key] = element;
        bindDirtyTracker(element);
    }
    return element;
}

function ensureElements() {
    if (!stagedList) stagedList = document.getElementById('staged-items');
    if (!modelSelect) modelSelect = document.getElementById('model-select');
    if (!modelFilterToggle) modelFilterToggle = document.getElementById('model-filter-vr');
    if (!addButton) addButton = document.getElementById('btn-add-to-queue');
    if (!browseFilesButton) browseFilesButton = document.getElementById('btn-browse-files');
    if (!dropZone) dropZone = document.getElementById('drop-zone');
    if (!manualPathInput) manualPathInput = document.getElementById('manual-path-input');
    if (!manualPathButton) manualPathButton = document.getElementById('btn-add-manual-path');
    if (!recommendButton) recommendButton = document.getElementById('btn-recommend-parameters');
    registerOptionInput('smooth', 'queue-opt-smooth');
    registerOptionInput('prominence', 'queue-opt-prominence');
    registerOptionInput('minProminence', 'queue-opt-min-prominence');
    registerOptionInput('maxSlope', 'queue-opt-max-slope');
    registerOptionInput('boostSlope', 'queue-opt-boost-slope');
    registerOptionInput('minSlope', 'queue-opt-min-slope');
    registerOptionInput('merge', 'queue-opt-merge');
    registerOptionInput('fftDenoise', 'queue-opt-fft-denoise');
    registerOptionInput('fftFrames', 'queue-opt-fft-frames');
    registerOptionInput('fftWindow', 'queue-opt-fft-window');
}

function toast(key, fallback, type = 'success', count) {
    let message = fallback;
    switch (key) {
        case 'select':
            message = I18n.t('queue.toast_select');
            break;
        case 'dialog':
            message = I18n.t('queue.toast_dialog');
            break;
        case 'added': {
            const template = I18n.t('queue.toast_added');
            const total = typeof count === 'number' ? count : staged.size || 0;
            message = template.replace('{count}', total);
            break;
        }
        case 'skipped':
            message = I18n.t('queue.toast_skipped');
            break;
        case 'unsupported':
            message = I18n.t('add.toast_unsupported');
            break;
        case 'drop_failed':
            message = I18n.t('add.toast_drop_failed');
            break;
        case 'drop_skipped':
            message = I18n.t('add.toast_drop_skipped');
            break;
        case 'browser_no_path':
            message = I18n.t('add.toast_browser_no_path');
            break;
        default:
            break;
    }
    showToast(message || fallback, type);
}

function renderStagedItems() {
    ensureElements();
    if (!stagedList) return;
    stagedList.innerHTML = '';
    if (addButton) {
        if (modelSelect?.disabled) {
            addButton.disabled = true;
        } else {
            addButton.disabled = staged.size === 0;
        }
    }
    if (staged.size === 0) {
        const empty = document.createElement('div');
        empty.className = 'staging__empty text-muted';
        empty.dataset.i18n = 'queue.no_staged';
        empty.textContent = 'No files staged.';
        stagedList.appendChild(empty);
        I18n.apply();
        return;
    }
    const fragment = document.createDocumentFragment();
    staged.forEach((item) => {
        const entry = document.createElement('div');
        entry.className = 'staging__item';

        const name = document.createElement('div');
        name.className = 'staging__name';
        name.textContent = item.name;
        entry.appendChild(name);

        const path = document.createElement('div');
        path.className = 'text-muted staging__path';
        path.textContent = item.path;
        entry.appendChild(path);

        const actions = document.createElement('div');
        actions.className = 'flex gap-sm';

        const removeButton = document.createElement('button');
        removeButton.className = 'button button--ghost';
        removeButton.dataset.i18n = 'queue.remove';
        removeButton.textContent = 'Remove';
        removeButton.addEventListener('click', () => {
            staged.delete(item.key);
            renderStagedItems();
        });
        actions.appendChild(removeButton);

        entry.appendChild(actions);
        fragment.appendChild(entry);
    });
    stagedList.appendChild(fragment);
    I18n.apply();
}

function applyDefaultOptions() {
    ensureElements();
    const defaults = State.get('settings')?.default_postprocess || {};

    const setNumeric = (input, value, fallbackKey) => {
        if (!input || trackedInputs.has(input)) return;
        if (value === undefined || value === null || Number.isNaN(value)) {
            input.value = DEFAULT_OPTIONS[fallbackKey] ?? '';
        } else {
            input.value = value;
        }
    };

    const setOptional = (input, value) => {
        if (!input || trackedInputs.has(input)) return;
        if (value === undefined || value === null || value === '') {
            input.value = '';
        } else {
            input.value = value;
        }
    };

    const setBoolean = (input, value, fallbackKey) => {
        if (!input || trackedInputs.has(input)) return;
        if (value === undefined || value === null) {
            input.checked = Boolean(DEFAULT_OPTIONS[fallbackKey]);
        } else {
            input.checked = Boolean(value);
        }
    };

    setNumeric(optionInputs.smooth, defaults.smooth_window_frames, 'smooth');
    setNumeric(optionInputs.prominence, defaults.prominence_ratio, 'prominence');
    setNumeric(optionInputs.minProminence, defaults.min_prominence, 'minProminence');
    setNumeric(optionInputs.maxSlope, defaults.max_slope, 'maxSlope');
    setNumeric(optionInputs.boostSlope, defaults.boost_slope, 'boostSlope');
    setNumeric(optionInputs.minSlope, defaults.min_slope, 'minSlope');
    setNumeric(optionInputs.merge, defaults.merge_threshold_ms, 'merge');
    setBoolean(optionInputs.fftDenoise, defaults.fft_denoise, 'fftDenoise');
    setNumeric(optionInputs.fftFrames, defaults.fft_frames_per_component, 'fftFrames');
    setOptional(optionInputs.fftWindow, defaults.fft_window_frames);
}

function isSupportedVideo(path) {
    const lower = path.toLowerCase();
    const index = lower.lastIndexOf('.');
    if (index === -1) return false;
    return VIDEO_EXTENSIONS.has(lower.slice(index));
}

function considerPath(rawPath) {
    if (typeof rawPath !== 'string') return;
    const path = rawPath.trim();
    if (!path) return;
    const key = normaliseKey(path);
    if (staged.has(key)) {
        return;
    }
    if (!isSupportedVideo(path)) {
        toast('unsupported', 'Unsupported file type.', 'error');
        return;
    }
    staged.set(key, stageMetadata(path));
}

function stagePaths(paths) {
    if (!Array.isArray(paths) || paths.length === 0) {
        return 0;
    }
    let added = 0;
    paths.forEach((path) => {
        const before = staged.size;
        considerPath(path);
        if (staged.size > before) {
            added += 1;
        }
    });
    if (added > 0) {
        renderStagedItems();
    }
    return added;
}

function parseFileUri(entry) {
    if (!entry) return null;
    try {
        const url = new URL(entry.trim());
        if (url.protocol !== 'file:') {
            return null;
        }
        let pathname = decodeURIComponent(url.pathname || '');
        if (/^\/[A-Za-z]:/.test(pathname)) {
            pathname = pathname.slice(1);
        }
        return pathname.split("\\").join("/");
    } catch (error) {
        const trimmed = entry.trim();
        if (/^[A-Za-z]:\\/.test(trimmed)) {
            return trimmed;
        }
        return null;
    }
}

function pathsFromDrop(event) {
    const results = new Set();
    const dataTransfer = event?.dataTransfer || event?.originalEvent?.dataTransfer;
    if (!dataTransfer) {
        return [];
    }
    const extractPath = (file) => {
        if (!file) return null;
        if (typeof file.path === 'string' && file.path.length) return file.path;
        if (typeof file.pywebviewFullPath === 'string' && file.pywebviewFullPath.length) return file.pywebviewFullPath;
        if (typeof file.webkitRelativePath === 'string' && file.webkitRelativePath.length) return file.webkitRelativePath;
        if (typeof file.name === 'string' && file.name.length && typeof file.fullPath === 'string') return file.fullPath;
        return null;
    };
    const files = Array.from(dataTransfer.files || []);
    files.forEach((file) => {
        const path = extractPath(file);
        if (path) {
            results.add(path);
        }
    });
    const appendFromString = (value) => {
        if (!value) return;
        value.split(/\r?\n/).forEach((line) => {
            const path = parseFileUri(line);
            if (path) {
                results.add(path);
            }
        });
    };
    appendFromString(dataTransfer.getData?.('text/uri-list'));
    appendFromString(dataTransfer.getData?.('text/plain'));
    return Array.from(results);
}
function getNumber(input, fallback) {
    if (!input) return fallback;
    const value = Number(input.value);
    return Number.isFinite(value) ? value : fallback;
}

function getOptionalInt(input) {
    if (!input) return undefined;
    const trimmed = input.value.trim();
    if (!trimmed) return undefined;
    const value = Number(trimmed);
    return Number.isFinite(value) ? Math.trunc(value) : undefined;
}

function getPostprocessOptions() {
    const options = {
        smooth_window_frames: Math.trunc(getNumber(optionInputs.smooth, 3)),
        prominence_ratio: getNumber(optionInputs.prominence, 0.1),
        min_prominence: getNumber(optionInputs.minProminence, 0.0),
        max_slope: getNumber(optionInputs.maxSlope, 10.0),
        boost_slope: getNumber(optionInputs.boostSlope, 7.0),
        min_slope: getNumber(optionInputs.minSlope, 0.0),
        merge_threshold_ms: getNumber(optionInputs.merge, 120.0),
        fft_denoise: optionInputs.fftDenoise ? Boolean(optionInputs.fftDenoise.checked) : true,
        fft_frames_per_component: Math.trunc(getNumber(optionInputs.fftFrames, 10)),
    };
    const windowFrames = getOptionalInt(optionInputs.fftWindow);
    if (windowFrames !== undefined) {
        options.fft_window_frames = windowFrames;
    }
    return options;
}

function attachModelFilter() {
    ensureElements();
    if (!modelFilterToggle) return;
    modelFilterToggle.checked = modelFilterVrOnly;
    if (modelFilterToggle.dataset.filterBound) return;
    modelFilterToggle.addEventListener('change', () => {
        modelFilterVrOnly = Boolean(modelFilterToggle.checked);
        renderModels(State.get('models') || []);
    });
    modelFilterToggle.dataset.filterBound = '1';
}

function isVrModel(model) {
    if (!model) return false;
    const identifier = String(model.display_name || model.name || model.path || '').toLowerCase();
    return identifier.includes('vr');
}

function filterModels(models) {
    if (!Array.isArray(models)) return [];
    return models.filter((model) => {
        const vr = isVrModel(model);
        return modelFilterVrOnly ? vr : !vr;
    });
}

function renderModels(models) {
    ensureElements();
    if (modelFilterToggle) {
        modelFilterToggle.checked = modelFilterVrOnly;
    }
    if (!modelSelect) return;
    modelSelect.innerHTML = '';
    const filtered = filterModels(models);
    if (!filtered || filtered.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        const emptyKey = modelFilterVrOnly ? 'add.no_models_vr' : 'add.no_models_non_vr';
        option.dataset.i18n = emptyKey;
        option.textContent = I18n.t(emptyKey);
        modelSelect.appendChild(option);
        modelSelect.disabled = true;
        addButton?.setAttribute('disabled', 'disabled');
        renderStagedItems();
        return;
    }
    modelSelect.disabled = false;
    addButton?.removeAttribute('disabled');
    filtered.forEach((model) => {
        const option = document.createElement('option');
        option.value = model.path;
        option.textContent = model.display_name || model.name || model.path;
        modelSelect.appendChild(option);
    });
    const defaultModel = State.get('settings')?.default_model_path;
    const preferredPath = filtered.some((model) => model.path === defaultModel)
        ? defaultModel
        : filtered[0]?.path;
    if (preferredPath) {
        modelSelect.value = preferredPath;
        if (modelSelect.value !== preferredPath) {
            modelSelect.selectedIndex = 0;
        }
    } else {
        modelSelect.selectedIndex = 0;
    }
    renderStagedItems();
}

async function refreshQueue() {
    try {
        const data = await Api.get('/api/queue');
        State.setQueue(data || []);
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function enqueueFiles() {
    ensureElements();
    if (staged.size === 0) {
        toast('select', 'Select at least one video.', 'error');
        return;
    }
    const payload = {
        video_paths: Array.from(staged.values()).map((item) => item.path),
        model_path: modelSelect?.value || undefined,
        postprocess_options: getPostprocessOptions(),
    };
    try {
        const result = await Api.post('/api/queue/add', payload);
        if (result?.added_count) {
            toast('added', 'Added to queue.', 'success', result.added_count);
            staged.clear();
            renderStagedItems();
            await refreshQueue();
        } else if (result?.skipped?.length) {
            toast('skipped', 'All files skipped.', 'error');
        }
    } catch (error) {
        showToast(error.message, 'error');
    }
}

function attachFilePickers() {
    ensureElements();
    if (browseFilesButton) {
        browseFilesButton.addEventListener('click', async () => {
            const files = await Native.selectFiles();
            if (Array.isArray(files)) {
                stagePaths(files);
                return;
            }
            if (!Native.hasNativeDialogs()) {
                openHtmlFilePicker();
                return;
            }
            toast('dialog', 'File dialog not available.', 'error');
        });
    }
}

function submitManualPath() {
    ensureElements();
    if (!manualPathInput) return;
    const raw = manualPathInput.value.trim();
    if (!raw) {
        showToast(I18n.t('add.toast_enter_path'), 'info');
        manualPathInput.focus();
        return;
    }
    const key = normaliseKey(raw);
    const duplicate = staged.has(key);
    const supported = isSupportedVideo(raw);
    if (!supported) {
        toast('unsupported', 'Unsupported file type.', 'error');
        manualPathInput.focus();
        return;
    }
    if (duplicate) {
        toast('drop_skipped', 'No new files were staged.', 'info');
        manualPathInput.focus();
        return;
    }
    const added = stagePaths([raw]);
    if (added > 0) {
        manualPathInput.value = '';
        manualPathInput.focus();
        return;
    }
    toast('drop_skipped', 'No new files were staged.', 'info');
    manualPathInput.focus();
}

function attachManualPathInput() {
    ensureElements();
    if (manualPathButton) {
        manualPathButton.addEventListener('click', (event) => {
            event.preventDefault();
            submitManualPath();
        });
    }
    if (manualPathInput) {
        manualPathInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                submitManualPath();
            }
        });
    }
}

function attachDropZone() {
    ensureElements();
    if (!dropZone) return;
    dropZone.addEventListener('dragover', (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (event?.dataTransfer) {
            event.dataTransfer.dropEffect = 'copy';
        }
        dropZone.classList.add('drag-over');
    });
    dropZone.addEventListener('dragleave', (event) => {
        event.preventDefault();
        event.stopPropagation();
        dropZone.classList.remove('drag-over');
    });
    dropZone.addEventListener('drop', (event) => {
        dropZone.classList.remove('drag-over');
        const paths = pathsFromDrop(event);
        const added = stagePaths(paths);
        if (added > 0) {
            event.preventDefault();
            event.stopPropagation();
        }
    });
}

function subscribeState() {
    State.subscribe('models', renderModels);
    State.subscribe('settings', () => {
        renderModels(State.get('models') || []);
        applyDefaultOptions();
    });
}

async function recommendParameters() {
    ensureElements();
    if (staged.size === 0) {
        showToast(I18n.t('add.recommend_no_video'), 'error');
        return;
    }
    if (!modelSelect?.value) {
        showToast(I18n.t('add.recommend_no_model'), 'error');
        return;
    }
    
    // Get first staged video
    const firstVideo = Array.from(staged.values())[0];
    if (!firstVideo) {
        showToast(I18n.t('add.recommend_no_video'), 'error');
        return;
    }
    
    if (recommendButton) {
        recommendButton.disabled = true;
        recommendButton.textContent = I18n.t('add.recommend_analyzing');
    }
    
    try {
        const payload = {
            video_path: firstVideo.path,
            model_path: modelSelect.value,
        };
        const response = await Api.post('/api/recommend-parameters', payload);
        
        if (response && response.recommended_options) {
            recommendedValues = response.recommended_options;
            showRecommendedValues(response);
            showToast(I18n.t('add.recommend_success'), 'success');
        } else {
            showToast(I18n.t('add.recommend_failed'), 'error');
        }
    } catch (error) {
        const errorMsg = `${I18n.t('add.recommend_failed_error')}: ${error.message}`;
        showToast(errorMsg, 'error');
    } finally {
        if (recommendButton) {
            recommendButton.disabled = false;
            recommendButton.textContent = I18n.t('add.recommend_parameters');
        }
    }
}

function showRecommendedValues(response) {
    const options = response.recommended_options || {};
    const reasoning = response.reasoning || '';
    
    // Map parameter names
    const paramMap = {
        smooth: { key: 'smooth_window_frames', element: 'recommended-smooth', button: 'btn-apply-smooth' },
        prominence: { key: 'prominence_ratio', element: 'recommended-prominence', button: 'btn-apply-prominence' },
        minProminence: { key: 'min_prominence', element: 'recommended-min-prominence', button: 'btn-apply-min-prominence' },
        maxSlope: { key: 'max_slope', element: 'recommended-max-slope', button: 'btn-apply-max-slope' },
        boostSlope: { key: 'boost_slope', element: 'recommended-boost-slope', button: 'btn-apply-boost-slope' },
        minSlope: { key: 'min_slope', element: 'recommended-min-slope', button: 'btn-apply-min-slope' },
        merge: { key: 'merge_threshold_ms', element: 'recommended-merge', button: 'btn-apply-merge' },
        fftFrames: { key: 'fft_frames_per_component', element: 'recommended-fft-frames', button: 'btn-apply-fft-frames' },
    };
    
    let hasRecommendations = false;
    for (const [paramKey, config] of Object.entries(paramMap)) {
        const value = options[config.key];
        if (value !== undefined && value !== null) {
            hasRecommendations = true;
            const valueElement = document.getElementById(config.element);
            const buttonElement = document.getElementById(config.button);
            
            if (valueElement) {
                valueElement.textContent = `${I18n.t('add.recommend_value')}: ${value}`;
                valueElement.style.display = 'inline';
            }
            if (buttonElement) {
                buttonElement.style.display = 'inline-block';
                // Apply i18n to button text if it has data-i18n attribute
                if (buttonElement.dataset.i18n) {
                    buttonElement.textContent = I18n.t(buttonElement.dataset.i18n);
                }
            }
        }
    }
    
    // Show "Apply All" button if there are recommendations
    const applyAllButton = document.getElementById('btn-apply-all-recommend');
    if (applyAllButton) {
        if (hasRecommendations) {
            applyAllButton.style.display = 'inline-block';
            if (applyAllButton.dataset.i18n) {
                applyAllButton.textContent = I18n.t(applyAllButton.dataset.i18n);
            }
        } else {
            applyAllButton.style.display = 'none';
        }
    }
    
    // Show reasoning if available
    if (reasoning) {
        console.log('Recommendation reasoning:', reasoning);
    }
}

function getElementIdForParam(paramKey) {
    // Map paramKey to actual HTML element ID
    const idMap = {
        smooth: 'smooth',
        prominence: 'prominence',
        minProminence: 'min-prominence',
        maxSlope: 'max-slope',
        boostSlope: 'boost-slope',
        minSlope: 'min-slope',
        merge: 'merge',
        fftFrames: 'fft-frames',
    };
    return idMap[paramKey] || paramKey;
}

function applyRecommendedValue(paramKey) {
    const paramMap = {
        smooth: { key: 'smooth_window_frames', input: optionInputs.smooth },
        prominence: { key: 'prominence_ratio', input: optionInputs.prominence },
        minProminence: { key: 'min_prominence', input: optionInputs.minProminence },
        maxSlope: { key: 'max_slope', input: optionInputs.maxSlope },
        boostSlope: { key: 'boost_slope', input: optionInputs.boostSlope },
        minSlope: { key: 'min_slope', input: optionInputs.minSlope },
        merge: { key: 'merge_threshold_ms', input: optionInputs.merge },
        fftFrames: { key: 'fft_frames_per_component', input: optionInputs.fftFrames },
    };
    
    const config = paramMap[paramKey];
    if (!config || !recommendedValues[config.key]) {
        return;
    }
    
    const value = recommendedValues[config.key];
    if (config.input) {
        if (config.input.type === 'number') {
            config.input.value = value;
        } else if (config.input.type === 'checkbox') {
            config.input.checked = Boolean(value);
        }
        markDirty(config.input);
    }
    
    // Hide the recommendation UI for this parameter
    const elementId = getElementIdForParam(paramKey);
    const valueElement = document.getElementById(`recommended-${elementId}`);
    const buttonElement = document.getElementById(`btn-apply-${elementId}`);
    
    if (valueElement) {
        valueElement.style.display = 'none';
    }
    if (buttonElement) {
        buttonElement.style.display = 'none';
    }
    
    showToast(`${I18n.t('add.applied_value')}: ${value}`, 'success');
}

function applyAllRecommendedValues() {
    if (!recommendedValues || Object.keys(recommendedValues).length === 0) {
        showToast(I18n.t('add.no_recommendations'), 'info');
        return;
    }
    
    const paramMap = {
        smooth: { key: 'smooth_window_frames', input: optionInputs.smooth },
        prominence: { key: 'prominence_ratio', input: optionInputs.prominence },
        minProminence: { key: 'min_prominence', input: optionInputs.minProminence },
        maxSlope: { key: 'max_slope', input: optionInputs.maxSlope },
        boostSlope: { key: 'boost_slope', input: optionInputs.boostSlope },
        minSlope: { key: 'min_slope', input: optionInputs.minSlope },
        merge: { key: 'merge_threshold_ms', input: optionInputs.merge },
        fftFrames: { key: 'fft_frames_per_component', input: optionInputs.fftFrames },
    };
    
    let appliedCount = 0;
    for (const [paramKey, config] of Object.entries(paramMap)) {
        if (recommendedValues[config.key] !== undefined && recommendedValues[config.key] !== null) {
            const value = recommendedValues[config.key];
            if (config.input) {
                if (config.input.type === 'number') {
                    config.input.value = value;
                } else if (config.input.type === 'checkbox') {
                    config.input.checked = Boolean(value);
                }
                markDirty(config.input);
            }
            
            // Hide the recommendation UI for this parameter
            const elementId = getElementIdForParam(paramKey);
            const valueElement = document.getElementById(`recommended-${elementId}`);
            const buttonElement = document.getElementById(`btn-apply-${elementId}`);
            
            if (valueElement) {
                valueElement.style.display = 'none';
            }
            if (buttonElement) {
                buttonElement.style.display = 'none';
            }
            
            appliedCount++;
        }
    }
    
    if (appliedCount > 0) {
        const message = I18n.t('add.applied_all_values').replace('{count}', appliedCount);
        showToast(message, 'success');
    } else {
        showToast(I18n.t('add.no_recommendations'), 'info');
    }
}

function attachRecommendButton() {
    ensureElements();
    if (recommendButton && !recommendButton.dataset.recommendBound) {
        recommendButton.addEventListener('click', recommendParameters);
        recommendButton.dataset.recommendBound = '1';
    }
    
    // Attach apply all button
    const applyAllButton = document.getElementById('btn-apply-all-recommend');
    if (applyAllButton && !applyAllButton.dataset.applyAllBound) {
        applyAllButton.addEventListener('click', applyAllRecommendedValues);
        applyAllButton.dataset.applyAllBound = '1';
        // Apply i18n to button text
        if (applyAllButton.dataset.i18n) {
            applyAllButton.textContent = I18n.t(applyAllButton.dataset.i18n);
        }
    }
    
    // Attach apply buttons and apply i18n
    document.querySelectorAll('.btn-apply-recommend').forEach((button) => {
        if (button.dataset.applyBound) return;
        button.addEventListener('click', (e) => {
            const paramKey = e.target.dataset.param;
            if (paramKey) {
                applyRecommendedValue(paramKey);
            }
        });
        button.dataset.applyBound = '1';
        // Apply i18n to button text
        if (button.dataset.i18n) {
            button.textContent = I18n.t(button.dataset.i18n);
        }
    });
    
    // Apply i18n to recommend button
    if (recommendButton && recommendButton.dataset.i18n) {
        recommendButton.textContent = I18n.t(recommendButton.dataset.i18n);
    }
}

export const AddView = {
    init() {
        ensureElements();
        attachModelFilter();
        attachFilePickers();
        attachManualPathInput();
        attachDropZone();
        attachRecommendButton();
        addButton?.addEventListener('click', enqueueFiles);
        subscribeState();
        renderModels(State.get('models') || []);
        applyDefaultOptions();
        renderStagedItems();
    },
    show() {
        // Re-attach recommend button when view is shown
        attachRecommendButton();
        // Re-apply i18n when view is shown
        I18n.apply();
    },
};

export default AddView;

if (typeof window !== 'undefined') {
    window.addEventListener('native:files-dropped', (event) => {
        const detail = event?.detail;
        const paths = Array.isArray(detail) ? detail : [];
        const added = stagePaths(paths);
        if (paths.length && added === 0) {
            toast('drop_skipped', 'No new files were staged.', 'info');
        }
    });
}

function ensureHtmlPicker() {
    if (htmlFileInput) return htmlFileInput;
    htmlFileInput = document.createElement('input');
    htmlFileInput.type = 'file';
    htmlFileInput.multiple = true;
    htmlFileInput.accept = Array.from(VIDEO_EXTENSIONS).join(',');
    htmlFileInput.style.display = 'none';
    htmlFileInput.addEventListener('change', () => {
        const files = Array.from(htmlFileInput?.files || []);
        if (!files.length) return;
        const paths = [];
        const missingPaths = [];
        files.forEach((file) => {
            console.log(file);
            const path = typeof file?.path === 'string' && file.path ? file.path : null;
            if (path) {
                paths.push(path);
            } else {
                missingPaths.push(file.name);
            }
        });
        console.log({ paths, missingPaths });
        const added = stagePaths(paths);
        if (missingPaths.length) {
            toast('browser_no_path', 'Browser security blocks access to file paths. Please use the desktop app.', 'error');
        }
        if (added === 0 && !missingPaths.length) {
            toast('drop_skipped', 'No new files were staged.', 'info');
        }
        htmlFileInput.value = '';
    });
    document.body.appendChild(htmlFileInput);
    return htmlFileInput;
}

function openHtmlFilePicker() {
    const input = ensureHtmlPicker();
    if (!input) {
        toast('dialog', 'File dialog not available.', 'error');
        return;
    }
    input.value = '';
    input.click();
}
