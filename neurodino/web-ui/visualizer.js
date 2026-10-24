function setupNeuroDino() {
    // Inject weights from Python
    const weights = __WEIGHTS_PLACEHOLDER__;
    window.useBezier = false;
    window.edgeWidth = 0.5;
    window.useProportionalWidth = false;
    window.useProportionalOpacity = false;
    window.useWeightColor = false;
    window.usePixelNodes = false;
    window.useNodeActivationColor = false;
    window.showBiases = true;
    window.posColor = "rgb(0, 0, 255)";
    window.negColor = "rgb(255, 0, 0)";
    window.defaultEdgeColor = "rgb(80, 80, 80)";
    window.nodeColor = "white";
    window.nodeBorderColor = "#333333";
    window.edgeOpacity = 1.0;
    window.showActiveEdgesOnly = false;

    // --- UI Control Functions (Global) ---
    window.updateNeuroVal = function (globalVar, value, displayId, displayVal) {
        window[globalVar] = parseFloat(value);
        if (displayId) {
            const el = document.getElementById(displayId);
            if (el) el.innerText = displayVal || value;
        }
    };

    window.toggleNeuroCheck = function (elemId, globalVar) {
        const el = document.getElementById('neuro_' + elemId);
        if (!el) return;

        const isChecked = el.classList.contains('checked');
        if (isChecked) {
            el.classList.remove('checked');
            window[globalVar] = false;
        } else {
            el.classList.add('checked');
            window[globalVar] = true;
        }

        // Special handling for Weight Color toggle to show/hide pickers
        if (elemId === 'weight_color_check') {
            const weightContainer = document.getElementById('neuro-weight-colors');
            const defaultContainer = document.getElementById('neuro-default-color');

            if (window[globalVar]) {
                // Weight Color ON: Show Pos/Neg, Hide Default
                if (weightContainer) weightContainer.style.display = 'block';
                if (defaultContainer) defaultContainer.style.display = 'none';
            } else {
                // Weight Color OFF: Hide Pos/Neg, Show Default
                if (weightContainer) weightContainer.style.display = 'none';
                if (defaultContainer) defaultContainer.style.display = 'block';
            }
        }



        // Special handling for Node Activation Color toggle
        if (elemId === 'activation_color_check') {
            const actContainer = document.getElementById('neuro-activation-colors');
            if (actContainer) {
                actContainer.style.display = window[globalVar] ? 'block' : 'none';
            }
        }

        // Recalculate Accordion Height if it's open
        const content = document.getElementById('neuro-controls-content');
        if (content && content.style.maxHeight) {
            // Wait for display change to render, then update height
            setTimeout(() => {
                content.style.maxHeight = (content.scrollHeight + 50) + "px";
            }, 10);
        }
    };

    window.updateNeuroColor = function (globalVar, value) {
        window[globalVar] = value;
    };


    window.toggleCustomControls = function () {
        const content = document.getElementById('neuro-controls-content');
        const arrow = document.getElementById('neuro-arrow');

        if (content.style.maxHeight) {
            content.style.maxHeight = null;
            content.style.paddingTop = "0px";
            content.style.paddingBottom = "0px";
            content.style.opacity = "0";
            arrow.style.transform = "rotate(-90deg)";
        } else {
            // Add extra height for the padding we are about to add (10px top + 10px bottom = 20px)
            content.style.maxHeight = (content.scrollHeight + 50) + "px";
            content.style.paddingTop = "10px";
            content.style.paddingBottom = "10px"; // match css
            content.style.opacity = "1";
            arrow.style.transform = "rotate(0deg)";
        }
    };

    window.toggleNeuroGroup = function (groupId, arrowId) {
        const content = document.getElementById(groupId);
        const arrow = document.getElementById(arrowId);
        const parentContent = document.getElementById('neuro-controls-content');

        if (content.style.maxHeight && content.style.maxHeight !== "0px") {
            // Collapse
            content.style.maxHeight = "0px";
            content.style.opacity = "0";
            content.style.marginBottom = "0px";
            if (arrow) arrow.style.transform = "rotate(-90deg)";
        } else {
            // Expand
            content.style.maxHeight = (content.scrollHeight + 20) + "px";
            content.style.opacity = "1";
            content.style.marginBottom = "20px";
            if (arrow) arrow.style.transform = "rotate(0deg)";
        }

        // Parent Height Recalculation
        if (parentContent && parentContent.style.maxHeight) {
            setTimeout(() => {
                // Determine new height needed. 
                // We add a large buffer because 'scrollHeight' might not update instantly during transition,
                // and max-height doesn't force height, just limits it. 
                // So setting it generously avoids cutting off content.
                parentContent.style.maxHeight = (parentContent.scrollHeight + content.scrollHeight + 200) + "px";
            }, 50);
        }
    };
    // -------------------------------------

    // Smooth Transition States
    window.smoothEdgeWidth = 2.0;
    window.smoothRadius = 10.0;
    window.smoothEdgeOpacity = 1.0;
    window.smoothLayerSpacing = 290;

    window.smoothLayerSpacing = 290;

    // Target Vertical Spacings (Controlled by UI)
    window.vSpacingInput = 30;
    window.vSpacingHidden = 10;
    window.vSpacingOutput = 30;

    // Smooth Variables (Initialized to target)
    window.smoothVSpacingInput = 30;
    window.smoothVSpacingHidden = 10;
    window.smoothVSpacingOutput = 30;
    window.smoothVSpacingOutput = 40;

    window.smoothPropFactor = 0.0;
    window.smoothPropOpacityFactor = 0.0;
    window.smoothBezierFactor = 0.0;
    window.smoothNodeColorFactor = 0.0;
    window.smoothActiveFactor = 0.0;

    window.layerSpacing = 290;
    window.targetRadius = 5;
    window.latestData = null;
    window.vSpacingInput = 30;
    window.vSpacingHidden = 10;
    window.vSpacingHidden = 10;
    window.vSpacingOutput = 40;

    // Zoom & Pan State
    window.vizScale = 1;
    window.panX = 0;
    window.panY = 0;
    window.isDragging = false;
    window.lastX = 0;
    window.lastY = 0;

    // Interaction State
    window.activeNode = null; // {layer: 'input'|'hidden'|'output', index: 0}
    window.nodePositions = []; // List of {x, y, r, layer, index} populated every frame

    // Main Draw Function (Updates Data ONLY)
    window.drawBrain = function (data) {
        window.latestData = data;

        // Start Loop if not started (idempotent check ideally, 
        // but we can just rely on the separate loop starter)
    };

    // Animation Loop
    function renderLoop() {
        requestAnimationFrame(renderLoop);

        // Smooth Parameter Interpolation
        if (window.smoothEdgeWidth === undefined) window.smoothEdgeWidth = window.edgeWidth;
        // Lerp factor 0.1 for smooth transition
        window.smoothEdgeWidth += (window.edgeWidth - window.smoothEdgeWidth) * 0.1;

        // Clamp to avoid tiny jitter when close
        if (Math.abs(window.edgeWidth - window.smoothEdgeWidth) < 0.001) {
            window.smoothEdgeWidth = window.edgeWidth;
        }

        // Smooth Radius Interpolation
        if (window.smoothRadius === undefined) window.smoothRadius = window.targetRadius;
        window.smoothRadius += (window.targetRadius - window.smoothRadius) * 0.1;
        if (Math.abs(window.targetRadius - window.smoothRadius) < 0.01) window.smoothRadius = window.targetRadius;

        // Smooth Opacity Interpolation
        if (window.smoothEdgeOpacity === undefined) window.smoothEdgeOpacity = window.edgeOpacity;
        window.smoothEdgeOpacity += (window.edgeOpacity - window.smoothEdgeOpacity) * 0.1;
        if (Math.abs(window.edgeOpacity - window.smoothEdgeOpacity) < 0.001) window.smoothEdgeOpacity = window.edgeOpacity;

        // Smooth Layer Spacing Interpolation
        if (window.smoothLayerSpacing === undefined) window.smoothLayerSpacing = window.layerSpacing;
        window.smoothLayerSpacing += (window.layerSpacing - window.smoothLayerSpacing) * 0.1;
        if (Math.abs(window.layerSpacing - window.smoothLayerSpacing) < 0.1) window.smoothLayerSpacing = window.layerSpacing;

        // Smooth Vertical Spacing Interpolation
        if (window.smoothVSpacingInput === undefined) window.smoothVSpacingInput = window.vSpacingInput;
        window.smoothVSpacingInput += (window.vSpacingInput - window.smoothVSpacingInput) * 0.1;
        if (Math.abs(window.vSpacingInput - window.smoothVSpacingInput) < 0.1) window.smoothVSpacingInput = window.vSpacingInput;

        if (window.smoothVSpacingHidden === undefined) window.smoothVSpacingHidden = window.vSpacingHidden;
        window.smoothVSpacingHidden += (window.vSpacingHidden - window.smoothVSpacingHidden) * 0.1;
        if (Math.abs(window.vSpacingHidden - window.smoothVSpacingHidden) < 0.1) window.smoothVSpacingHidden = window.vSpacingHidden;

        if (window.smoothVSpacingOutput === undefined) window.smoothVSpacingOutput = window.vSpacingOutput;
        window.smoothVSpacingOutput += (window.vSpacingOutput - window.smoothVSpacingOutput) * 0.1;
        if (Math.abs(window.vSpacingOutput - window.smoothVSpacingOutput) < 0.1) window.smoothVSpacingOutput = window.vSpacingOutput;

        // Smooth Proportional Width Factor (Toggle Animation)
        const targetPropFactor = window.useProportionalWidth ? 1.0 : 0.0;
        if (window.smoothPropFactor === undefined) window.smoothPropFactor = targetPropFactor;
        window.smoothPropFactor += (targetPropFactor - window.smoothPropFactor) * 0.1;

        // Smooth Proportional Opacity Factor
        const targetPropOpacityFactor = window.useProportionalOpacity ? 1.0 : 0.0;
        if (window.smoothPropOpacityFactor === undefined) window.smoothPropOpacityFactor = targetPropOpacityFactor;
        window.smoothPropOpacityFactor += (targetPropOpacityFactor - window.smoothPropOpacityFactor) * 0.1;

        // Smooth Bezier Factor (0.0 = Straight, 1.0 = Curved)
        const targetBezier = window.useBezier ? 1.0 : 0.0;
        if (window.smoothBezierFactor === undefined) window.smoothBezierFactor = targetBezier;
        window.smoothBezierFactor += (targetBezier - window.smoothBezierFactor) * 0.1;

        // Smooth Node Color Factor
        const targetNodeColor = window.useNodeActivationColor ? 1.0 : 0.0;
        if (window.smoothNodeColorFactor === undefined) window.smoothNodeColorFactor = targetNodeColor;
        window.smoothNodeColorFactor += (targetNodeColor - window.smoothNodeColorFactor) * 0.1;

        let targetActiveFactor = window.showActiveEdgesOnly ? 1.0 : 0.0;
        window.smoothActiveFactor += (targetActiveFactor - window.smoothActiveFactor) * 0.1;

        // --- Data Interpolation (Signal Smoothing) ---
        if (!window.displayData && window.latestData) {
            // First frame initialization (Deep Clone to avoid ref issues)
            window.displayData = JSON.parse(JSON.stringify(window.latestData));
        }

        if (window.displayData && window.latestData) {
            const lerpFactor = 0.15; // Tuning: 0.15 gives a nice fluid feel

            // Helper to Lerp Value or Object->Value
            const lerpVal = (current, target) => {
                const cVal = (typeof current === 'object' && current !== null) ? current.val : current;
                const tVal = (typeof target === 'object' && target !== null) ? target.val : target;

                // If structure mismatch or undefined, jump to target
                if (cVal === undefined || tVal === undefined) return target;

                const newVal = cVal + (tVal - cVal) * lerpFactor;

                if (typeof current === 'object' && current !== null) {
                    current.val = newVal;
                    return current;
                }
                return newVal;
            };

            // Interpolate Inputs
            if (window.displayData.inputs && window.latestData.inputs) {
                for (let i = 0; i < window.latestData.inputs.length; i++) {
                    // Ensure source array is large enough
                    if (window.displayData.inputs[i] === undefined) window.displayData.inputs[i] = window.latestData.inputs[i];
                    else window.displayData.inputs[i] = lerpVal(window.displayData.inputs[i], window.latestData.inputs[i]);
                }
            }

            // Interpolate Hidden
            if (window.displayData.hidden && window.latestData.hidden) {
                for (let i = 0; i < window.latestData.hidden.length; i++) {
                    if (window.displayData.hidden[i] === undefined) window.displayData.hidden[i] = window.latestData.hidden[i];
                    else window.displayData.hidden[i] = lerpVal(window.displayData.hidden[i], window.latestData.hidden[i]);
                }
            }

            // Interpolate Outputs
            if (window.displayData.outputs && window.latestData.outputs) {
                for (let i = 0; i < window.latestData.outputs.length; i++) {
                    if (window.displayData.outputs[i] === undefined) window.displayData.outputs[i] = window.latestData.outputs[i];
                    else window.displayData.outputs[i] = lerpVal(window.displayData.outputs[i], window.latestData.outputs[i]);
                }
            }
        }

        const canvas = document.getElementById('brainCanvas');
        if (!canvas) return;

        // Initialize Events Once
        if (!canvas.listenersAdded) {
            canvas.listenersAdded = true;

            canvas.addEventListener('mousedown', (e) => {
                const rect = canvas.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;

                // Get World Coordinates
                const dpr = window.devicePixelRatio || 1;
                // Note: nodePositions are stored in LOGICAL coordinates (unscaled by dpr, but scaled by vizScale in world?)
                // Actually my nodePositions capture logic below uses the transform? 
                // Let's ensure nodePositions stores WORLD coordinates (before Pan/Scale).
                // Wait, if I grab x,y inside drawLayer, that is in World Space (after translate/scale).
                // No, ctx calls use Local Coords.
                // ctx.translate(panX, panY); ctx.scale(scale); ctx.arc(x,y).
                // So 'x, y' in drawLayer are LOCAL coordinates relative to the scene origin (0,0).
                // So we need to transform Mouse -> View -> World.

                const worldX = (mouseX - window.panX) / window.vizScale;
                const worldY = (mouseY - window.panY) / window.vizScale;

                // Check collisions
                let hitNode = null;
                for (const node of window.nodePositions) {
                    const dx = worldX - node.x;
                    const dy = worldY - node.y;
                    if (dx * dx + dy * dy < node.r * node.r) {
                        hitNode = node;
                        break;
                    }
                }

                if (hitNode) {
                    window.activeNode = { layer: hitNode.layer, index: hitNode.index };
                    window.isDragging = false; // Don't pan if we clicked a node
                } else {
                    window.activeNode = null;
                    window.isDragging = true;
                    window.lastX = e.clientX;
                    window.lastY = e.clientY;
                    canvas.style.cursor = 'grabbing';
                }
            });

            window.addEventListener('mouseup', () => {
                if (window.activeNode) {
                    window.activeNode = null; // Release hold
                }
                window.isDragging = false;
                if (canvas) canvas.style.cursor = 'grab';
            });

            canvas.addEventListener('mouseleave', () => {
                window.isDragging = false;
                if (canvas) canvas.style.cursor = 'grab';
            });

            canvas.addEventListener('mousemove', (e) => {
                if (!window.isDragging) return;
                const dx = e.clientX - window.lastX;
                const dy = e.clientY - window.lastY;
                window.panX += dx;
                window.panY += dy;
                window.lastX = e.clientX;
                window.lastY = e.clientY;
            });

            canvas.addEventListener('wheel', (e) => {
                e.preventDefault();
                const zoomIntensity = 0.0015;
                const rect = canvas.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;

                const worldX = (mouseX - window.panX) / window.vizScale;
                const worldY = (mouseY - window.panY) / window.vizScale;

                const factor = Math.exp(-e.deltaY * zoomIntensity);
                // Unlimited Zoom (0.001x to 1000x)
                const newScale = Math.min(Math.max(0.001, window.vizScale * factor), 1000);

                window.vizScale = newScale;
                window.panX = mouseX - worldX * newScale;
                window.panY = mouseY - worldY * newScale;
            });

            canvas.style.cursor = 'grab';
        }

        const data = window.displayData || window.latestData;
        if (!data || !weights) return;

        const ctx = canvas.getContext('2d');

        // Resize & Auto-Expand
        const pad = 40;
        const iCount = data.inputs.length;
        const hCount = data.hidden.length;
        const oCount = data.outputs.length;

        // Auto-Scale Spacing to prevent Overlap
        // Ensure spacing is at least (Diameter + 2px padding)
        const minSpacing = (window.smoothRadius * 2) + 2;

        // Use effective spacing (User setting OR Minimum required)
        const effSpacingInput = Math.max(window.smoothVSpacingInput, minSpacing);
        const effSpacingHidden = Math.max(window.smoothVSpacingHidden, minSpacing);
        const effSpacingOutput = Math.max(window.smoothVSpacingOutput, minSpacing);

        // Calculate needed height
        const hInput = (iCount - 1) * effSpacingInput;
        const hHidden = (hCount - 1) * effSpacingHidden;
        const hOutput = (oCount - 1) * effSpacingOutput;

        const contentHeight = Math.max(hInput, hHidden, hOutput);
        const neededHeight = contentHeight + (pad * 2);

        if (canvas.parentElement) {
            let clientW, clientH;

            // Windowed Mode: Auto-expand height
            clientW = canvas.parentElement.clientWidth;
            clientH = Math.max(850, neededHeight);
            canvas.style.width = clientW + 'px';
            canvas.style.height = clientH + 'px';

            // High-DPI Support
            const dpr = window.devicePixelRatio || 1;

            // Set physical size (resolution)
            canvas.width = clientW * dpr;
            canvas.height = clientH * dpr;
        }

        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        // Reset node positions for this frame
        window.nodePositions = [];

        // Verify pan/zoom
        ctx.save();

        // Apply High-DPI Scale first
        const dpr = window.devicePixelRatio || 1;
        ctx.scale(dpr, dpr);

        ctx.translate(window.panX, window.panY);
        ctx.scale(window.vizScale, window.vizScale);

        const layoutPad = 40;
        // input, hidden(center), output
        // Use Logical Width/Height for valid coordinates
        const logicalW = canvas.width / dpr;
        const logicalH = canvas.height / dpr;

        const cx = logicalW / 2;
        // Use smooth layer spacing
        const layerX = [cx - window.smoothLayerSpacing, cx, cx + window.smoothLayerSpacing];

        function getY(count, index, spacing) {
            // Distribute using specific spacing
            const colH = (count - 1) * spacing;
            const startY = (logicalH - colH) / 2;
            return startY + index * spacing;
        }

        // Draw Weights (Input -> Hidden)
        for (let i = 0; i < iCount; i++) {
            for (let j = 0; j < hCount; j++) {
                // Visibility Check
                let visible = true;
                if (window.activeNode) {
                    const an = window.activeNode;
                    // Connects if: Active is Input(i) OR Active is Hidden(j)
                    const connected = (an.layer === 'input' && an.index === i) ||
                        (an.layer === 'hidden' && an.index === j);
                    if (!connected) visible = false;
                }

                // Draw Faded or Full
                let baseAlpha = visible ? window.smoothEdgeOpacity : 0.02;
                let alpha = baseAlpha;

                const weight = weights.ih[j][i];

                if (visible) {
                    // Smooth Blend for Opacity: Uniform vs Proportional
                    // Proportional: Scale alpha by weight magnitude (min 0.1)
                    const propAlpha = Math.min(baseAlpha, Math.max(0.1, Math.abs(weight) * baseAlpha));
                    // Blend: baseAlpha (Uniform) -> propAlpha (Proportional)
                    alpha = baseAlpha + (propAlpha - baseAlpha) * window.smoothPropOpacityFactor;

                    // Signal-Based Visibility (Active Edges)
                    // Signal = Source Node Activation * Weight
                    const rawVal = data.inputs[i];
                    const sourceVal = (rawVal && rawVal.val !== undefined) ? rawVal.val : rawVal;
                    const signal = Math.abs(sourceVal * weight);
                    // Signal Alpha: Scale by signal strength (boosted 3x for visibility)
                    const signalAlpha = Math.min(baseAlpha, signal * 3.0);

                    // Blend: Standard Alpha -> Signal Alpha based on smoothActiveFactor
                    alpha = alpha + (signalAlpha - alpha) * window.smoothActiveFactor;
                }

                if (window.smoothEdgeWidth > 0.05) {
                    ctx.beginPath();
                    const y1 = getY(iCount, i, effSpacingInput);
                    const y2 = getY(hCount, j, effSpacingHidden);

                    ctx.moveTo(layerX[0], y1);

                    // Always use Bezier to allow interpolation (Straight <-> Curved)
                    const x1 = layerX[0];
                    const x2 = layerX[1];
                    // Bezier Factor: 0.0 (CPs at ends) -> 1.0 (CPs at midpoints)
                    const factor = window.smoothBezierFactor;

                    const cx1 = x1 + (x2 - x1) * (0.5 * factor);
                    const cy1 = y1;
                    const cx2 = x2 - (x2 - x1) * (0.5 * factor);
                    const cy2 = y2;
                    ctx.bezierCurveTo(cx1, cy1, cx2, cy2, x2, y2);

                    if (window.useWeightColor) {
                        ctx.strokeStyle = weight > 0 ? window.posColor : window.negColor;
                    } else {
                        ctx.strokeStyle = window.defaultEdgeColor;
                    }

                    ctx.globalAlpha = alpha;



                    // Smooth Blend: Uniform vs Proportional (Replaces above block visually if factor used)
                    const wUniform = window.smoothEdgeWidth;
                    const wProp = Math.abs(weight) * window.smoothEdgeWidth * 3;
                    ctx.lineWidth = wUniform + (wProp - wUniform) * window.smoothPropFactor;

                    ctx.stroke();
                    ctx.globalAlpha = 1.0;
                }
            }
        }

        // Draw Weights (Hidden -> Output)
        for (let j = 0; j < hCount; j++) {
            for (let k = 0; k < oCount; k++) {
                // Visibility Check
                let visible = true;
                if (window.activeNode) {
                    const an = window.activeNode;
                    const connected = (an.layer === 'hidden' && an.index === j) ||
                        (an.layer === 'output' && an.index === k);
                    if (!connected) visible = false;
                }
                let baseAlpha = visible ? window.smoothEdgeOpacity : 0.02;
                let alpha = baseAlpha;

                const weight = weights.ho[k][j];

                if (visible) {
                    // Smooth Blend for Opacity: Uniform vs Proportional
                    const propAlpha = Math.min(baseAlpha, Math.max(0.1, Math.abs(weight) * baseAlpha));
                    alpha = baseAlpha + (propAlpha - baseAlpha) * window.smoothPropOpacityFactor;

                    // Signal-Based Visibility
                    const rawVal = data.hidden[j];
                    const sourceVal = (rawVal && rawVal.val !== undefined) ? rawVal.val : rawVal;
                    const signal = Math.abs(sourceVal * weight);
                    const signalAlpha = Math.min(baseAlpha, signal * 3.0);

                    alpha = alpha + (signalAlpha - alpha) * window.smoothActiveFactor;
                }

                if (window.smoothEdgeWidth > 0.05) {
                    ctx.beginPath();
                    const y1 = getY(hCount, j, effSpacingHidden);
                    const y2 = getY(oCount, k, effSpacingOutput);

                    ctx.moveTo(layerX[1], y1);

                    // Always use Bezier to allow interpolation
                    const x1 = layerX[1];
                    const x2 = layerX[2];
                    const factor = window.smoothBezierFactor;

                    const cx1 = x1 + (x2 - x1) * (0.5 * factor);
                    const cy1 = y1;
                    const cx2 = x2 - (x2 - x1) * (0.5 * factor);
                    const cy2 = y2;
                    ctx.bezierCurveTo(cx1, cy1, cx2, cy2, x2, y2);

                    if (window.useWeightColor) {
                        ctx.strokeStyle = weight > 0 ? window.posColor : window.negColor;
                    } else {
                        ctx.strokeStyle = window.defaultEdgeColor;
                    }

                    ctx.globalAlpha = alpha;

                    // Smooth Blend: Uniform vs Proportional
                    const wUniform = window.smoothEdgeWidth;
                    const wProp = Math.abs(weight) * window.smoothEdgeWidth * 3;
                    ctx.lineWidth = wUniform + (wProp - wUniform) * window.smoothPropFactor;

                    ctx.stroke();
                    ctx.globalAlpha = 1.0;
                }
            }
        }



        function drawStats(ctx, data) {
            if (data.million_count !== undefined) {
                ctx.save();
                ctx.font = "12px 'PressStart2P', monospace";
                ctx.textAlign = "right";

                // Draw GEN (Red)
                ctx.fillStyle = "rgb(255, 80, 80)";
                ctx.fillText("GEN: " + (data.death_count || 1), ctx.canvas.width - 20, 25);

                // Draw 1M+ (Green)
                ctx.fillStyle = "rgb(80, 255, 80)";
                ctx.fillText("1M+: " + data.million_count, ctx.canvas.width - 20, 45);

                ctx.restore();
            }
        }

        function drawLayer(count, activations, x, spacing, layerName, labels = null, biases = null) {
            const startY = getY(count, 0, spacing);

            // Use smoothed radius
            const radius = window.smoothRadius;

            for (let i = 0; i < count; i++) {
                try {
                    const y = getY(count, i, spacing);
                    let val = activations ? activations[i] : 0;

                    // Robust Handling: Flatten arrays if nested JS arrays arrive
                    if (Array.isArray(val)) val = val[0];
                    if (val === undefined || val === null || isNaN(val)) val = 0;

                    // --- Node Visibility Logic ---
                    let visible = true;
                    if (window.activeNode) {
                        const an = window.activeNode;
                        // Show if Self
                        if (an.layer === layerName && an.index === i) visible = true;
                        // Show if Neighbor
                        else if (layerName === 'input' && an.layer === 'hidden') visible = true; // Is it ANY input? technically all inputs connect to all hiddens
                        else if (layerName === 'hidden' && an.layer === 'input') visible = true;
                        else if (layerName === 'hidden' && an.layer === 'output') visible = true;
                        else if (layerName === 'output' && an.layer === 'hidden') visible = true;
                        else visible = false;

                        // Refined Neighbor Logic: only connected?
                        // Since full dense, all Input<->Hidden are connected. All Hidden<->Output are connected.
                        // So if I select Input3, ALL hidden nodes are neighbors.
                        // If I select Hidden5, ALL inputs and ALL outputs are neighbors.
                        // If I select Output2, ALL hidden nodes are neighbors.
                        // So logical filtering:
                        // If Active is Input: Show Active Input, All Hiddens.
                        // If Active is Hidden: Show All Inputs, Active Hidden, All Outputs.
                        // If Active is Output: Show All Hiddens, Active Output.

                        // Actually, simpler visual:
                        // Fade everything out.
                        // Always show Active node full.
                        // If Active is Input: Fade all other Inputs. Show Hiddens (neighbors) full.
                        // If Active is Output: Fade all other Outputs. Show Hiddens (neighbors) full.
                        // If Active is Hidden: Fade all other Hiddens. Show Inputs and Outputs full.

                        // Let's implement this simpler node visibility logic:
                        if (an.layer === layerName && an.index !== i) visible = false; // Hide siblings
                        // Neighbors are strictly in adjacent layers
                        if (Math.abs(getLayerIdx(layerName) - getLayerIdx(an.layer)) > 1) visible = false; // Hide non-neighbors
                        // Wait, Input(0) and Output(2) diff is 2. So correct.
                    }
                    const alpha = visible ? 1.0 : 0.1;

                    ctx.globalAlpha = alpha;

                    ctx.beginPath();
                    ctx.fillStyle = window.nodeColor;
                    ctx.lineWidth = 0.5;
                    ctx.strokeStyle = window.nodeBorderColor;

                    if (window.usePixelNodes) {
                        // Rasterized Circle (Round Pixel)
                        // Dynamic pSize for better roundness
                        let pSize = Math.max(1, Math.floor(radius / 4));

                        for (let dy = -radius; dy <= radius; dy += pSize) {
                            for (let dx = -radius; dx <= radius; dx += pSize) {
                                const dist = Math.sqrt(dx * dx + dy * dy);

                                if (dist <= radius) {
                                    // Default to Border
                                    ctx.fillStyle = window.nodeBorderColor;

                                    // Inner Fill Logic (Radius - BorderThickness)
                                    // Standard border is 0.5 lineWidth, here let's make it 1 pSize unit
                                    if (dist <= radius - pSize) {
                                        ctx.fillStyle = window.nodeColor;

                                        // Activation Logic (Inner-most core)
                                        // val is 0.0 to 1.0. 
                                        // If we are deep enough inside relative to activation size?
                                        // Activation Radius = radius * 0.5 * val? No, just proportional fill.
                                        // Original logic: radius * 0.5 + val * (radius * 0.5)
                                        const actRadius = (radius * 0.5) + (val * radius * 0.5);
                                        if (dist <= actRadius) {
                                            // Blend Logic? Canvas doesn't support per-pixel alpha easily in this loop efficiently
                                            // So just decide check:
                                            // Activation color is black with alpha val.
                                            // Here we just make it dark gray magnitude?
                                            // Simpler: If within activation radius, draw activation color (black)
                                            // Logic: inner fill is white. Activation is black overlay.
                                            // If we are in activation zone, draw gray/black based on strength?
                                            // Improved: If val > 0.1 and dist <= (radius * 0.8 * val), draw Black.
                                            // Let's mimic original:
                                            // Original draws Fill(NodeColor) THEN Fill(BlackAlpha).
                                            // Here we pick ONE color for the pixel.

                                            // Mix NodeColor and Black based on val?
                                            // If NodeColor is White, result is Grey.
                                            // Simply: If dist < actRadius, draw Darker.
                                            if (dist <= radius * val) {
                                                ctx.fillStyle = `rgba(0,0,0,${val})`;
                                                // Note: rgba works with fillRect, it blends with canvas background (white? transparent?)
                                                // But we are drawing pixel-by-pixel. Overlap?
                                                // Actually, if we just set fillStyle to rgba(0,0,0,val) and draw rect
                                                // over the canvas, it's fine.
                                                // BUT we need to paint the NodeColor underneath first if transparency matters?
                                                // Yes.
                                            }
                                        }
                                    }

                                    // Draw Pixel
                                    // Snap to integer grid to avoid anti-aliasing artifacts
                                    const px = Math.floor(x + dx);
                                    const py = Math.floor(y + dy);

                                    // 1. Draw Solid Base (Hides background lines)
                                    // We must reset fillStyle to nodeColor or nodeBorderColor based on position
                                    if (dist <= radius - pSize) {
                                        ctx.fillStyle = window.nodeColor;
                                    } else {
                                        ctx.fillStyle = window.nodeBorderColor;
                                    }
                                    ctx.fillRect(px, py, pSize, pSize);

                                    // 2. Draw Semi-Transparent Activation on Top
                                    const absVal = Math.abs(val);
                                    if (dist <= radius - pSize) {
                                        if (dist <= radius * absVal) { // Math Fix
                                            if (window.useNodeActivationColor) {
                                                const color = val > 0 ? window.posColor : window.negColor;
                                                ctx.fillStyle = color;
                                                ctx.globalAlpha = Math.min(absVal, 1.0);
                                                ctx.fillRect(px, py, pSize, pSize);
                                                ctx.globalAlpha = 1.0;
                                            } else {
                                                ctx.fillStyle = `rgba(0, 0, 0, ${absVal})`;
                                                ctx.fillRect(px, py, pSize, pSize);
                                            }
                                        }
                                    }
                                }
                            }
                        }

                    } else {
                        // Original Vector Circle
                        ctx.fillStyle = window.nodeColor;
                        ctx.lineWidth = 0.5;
                        ctx.strokeStyle = window.nodeBorderColor;
                        ctx.beginPath();
                        ctx.arc(x, y, radius, 0, Math.PI * 2);
                        ctx.fill();
                        ctx.stroke();

                        // Activation
                        const absVal = Math.abs(val);
                        // Clamp Radius Calculation
                        // Math Fix: Use absVal for sizing. 
                        // Logic: Base inner circle is 0.5r. Grow to 1.0r with activation.
                        const actRadius = radius * 0.5 + Math.min(absVal, 1.0) * (radius * 0.5);

                        ctx.beginPath();
                        ctx.arc(x, y, actRadius, 0, Math.PI * 2);

                        if (window.useNodeActivationColor) {
                            // Color Mode
                            const color = val > 0 ? window.posColor : window.negColor;
                            ctx.fillStyle = color;
                            ctx.globalAlpha = Math.min(absVal, 1.0); // Use global alpha for hex colors
                            ctx.fill();
                            ctx.globalAlpha = 1.0;
                        } else {
                            // Grayscale Mode (Math Fix Applied)
                            ctx.fillStyle = `rgba(0,0,0,${Math.min(absVal, 1.0)})`;
                            ctx.fill();
                        }
                    }

                    // Bias Visualization (Indicator)
                    // Draw small dot/square on top-right rim
                    // Bias range is usually -0.5 to 0.5 or larger.

                    if (window.showBiases && biases && biases[i] !== undefined) {
                        const biasVal = Array.isArray(biases[i]) ? biases[i][0] : biases[i]; // Handle [val] format
                        const biasMag = Math.abs(biasVal);
                        // Color Logic: Red for Negative, Green for Positive
                        const biasColor = biasVal >= 0 ? "rgb(0, 255, 0)" : "rgb(255, 0, 0)";

                        if (window.usePixelNodes) {
                            // Pixel Indiciator on rim
                            const pSize = Math.max(1, Math.floor(radius / 4));
                            // Position: Top Right Corner relative to center
                            // 45 degrees. dx = r * 0.707
                            const offset = Math.floor(radius * 0.75);
                            const px = Math.floor(x + offset);
                            const py = Math.floor(y - offset);

                            ctx.fillStyle = biasColor;
                            ctx.fillRect(px, py, pSize * 2, pSize * 2); // Slightly larger dot
                        } else {
                            // Vector Indicator
                            const offset = radius * 0.8;
                            const bx = x + offset;
                            const by = y - offset;

                            ctx.beginPath();
                            ctx.arc(bx, by, radius * 0.3, 0, Math.PI * 2);
                            ctx.fillStyle = biasColor;
                            ctx.fill();
                            // Optional border for visibility?
                            // ctx.strokeStyle = "black";
                            // ctx.lineWidth = 0.5;
                            // ctx.stroke();
                        }
                    }

                    if (labels[i]) {
                        ctx.fillStyle = "rgb(84, 84, 84)";
                        ctx.font = "10px 'PressStart2P'";
                        ctx.textAlign = "right";
                        ctx.fillText(labels[i] + " " + val.toFixed(2), x - 12, y + 4);
                        ctx.textAlign = "left";
                    }

                } catch (err) {
                    // Suppress error to allow other nodes to draw
                    // console.error("Node draw error:", err); 
                }
            }
        }

        function getLayerIdx(name) {
            if (name === 'input') return 0;
            if (name === 'hidden') return 1;
            if (name === 'output') return 2;
            return -1;
        }

        drawLayer(iCount, data.inputs, layerX[0], effSpacingInput, 'input', ["Obj1 Dist", "Obj1 Act", "Obj1 W", "Obj2 Dist", "Obj2 Act", "Obj2 W", "Speed", "Gap", "DinoY", "DinoVel", "Air", "Duck"]);
        // Inputs have no bias usually (raw sensors).
        drawLayer(hCount, data.hidden, layerX[1], effSpacingHidden, 'hidden', null, weights.bh);
        drawLayer(oCount, data.outputs, layerX[2], effSpacingOutput, 'output', null, weights.bo);

        drawStats(ctx, data); // Draw 1M Counter

        // Labels Output
        const outLabels = ["JUMP", "DUCK", "RUN"];
        for (let i = 0; i < oCount; i++) {
            ctx.fillStyle = "rgb(84, 84, 84)";
            ctx.font = "10px 'PressStart2P'";
            ctx.fillText(outLabels[i] + " " + Math.round(data.outputs[i] * 100) + "%", layerX[2] + 15, getY(oCount, i, effSpacingOutput) + 4);
        }

        ctx.restore();
    }

    // Start loop
    requestAnimationFrame(renderLoop);
}
