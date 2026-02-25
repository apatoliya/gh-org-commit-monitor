(function () {
    'use strict';

    var DURATION_MS = 1200;

    function easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    function parseKpiValue(text) {
        var cleaned = text.replace(/,/g, '');
        var match = cleaned.match(/([\d.]+)/);
        if (!match) return null;
        return parseFloat(match[1]);
    }

    function formatNumber(num, originalText) {
        if (originalText.includes('(') && originalText.includes('%')) {
            var pctMatch = originalText.match(/\(([\d.]+%)\)/);
            var pctStr = pctMatch ? ' (' + pctMatch[1] + ')' : '';
            return Math.round(num).toLocaleString() + pctStr;
        }
        if (originalText.includes('%')) {
            return num.toFixed(1) + '%';
        }
        if (originalText.includes(',')) {
            return Math.round(num).toLocaleString();
        }
        if (Number.isInteger(num) || num === Math.round(num)) {
            return Math.round(num).toString();
        }
        return num.toFixed(1);
    }

    function animateCounter(element) {
        var finalText = element.textContent.trim();
        if (!finalText || finalText === '0') return;

        var finalValue = parseKpiValue(finalText);
        if (finalValue === null || finalValue === 0) return;

        if (element.dataset.animated === finalText) return;
        element.dataset.animated = finalText;

        var startTime = null;

        function step(timestamp) {
            if (!startTime) startTime = timestamp;
            var progress = Math.min((timestamp - startTime) / DURATION_MS, 1);
            var easedProgress = easeOutCubic(progress);
            var currentValue = easedProgress * finalValue;

            element.textContent = formatNumber(currentValue, finalText);

            if (progress < 1) {
                requestAnimationFrame(step);
            } else {
                element.textContent = finalText;
            }
        }

        element.textContent = '0';
        requestAnimationFrame(step);
    }

    function scanForKpiValues(root) {
        var elements = [];
        if (root.classList && root.classList.contains('kpi-value')) {
            elements.push(root);
        }
        if (root.querySelectorAll) {
            var found = root.querySelectorAll('.kpi-value');
            for (var i = 0; i < found.length; i++) {
                elements.push(found[i]);
            }
        }
        return elements;
    }

    var observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
            mutation.addedNodes.forEach(function (node) {
                if (node.nodeType !== 1) return;
                var kpiElements = scanForKpiValues(node);
                kpiElements.forEach(function (el) {
                    animateCounter(el);
                });
            });
        });
    });

    observer.observe(document.body, { childList: true, subtree: true });
})();
