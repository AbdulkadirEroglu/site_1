const initAdminThemeToggle = () => {
    const toggle = document.querySelector('[data-theme-toggle]');
    if (!toggle) return;

    const storageKey = 'admin-theme';
    const icon = toggle.querySelector('[data-theme-icon]');
    const apply = (mode) => {
        const isDark = mode === 'dark';
        document.body.classList.toggle('theme-dark', isDark);
        toggle.setAttribute('aria-pressed', isDark ? 'true' : 'false');
        toggle.setAttribute('aria-label', isDark ? 'Switch to light theme' : 'Switch to dark theme');
        if (icon) {
            icon.textContent = isDark ? 'Light' : 'Dark';
        }
    };

    let current = window.localStorage.getItem(storageKey) || 'light';
    apply(current);

    toggle.addEventListener('click', () => {
        current = current === 'dark' ? 'light' : 'dark';
        apply(current);
        window.localStorage.setItem(storageKey, current);
    });
};

const initImageDeleteButtons = () => {
    const buttons = document.querySelectorAll('[data-image-delete-button]');
    if (!buttons.length) return;

    buttons.forEach((button) => {
        const targetId = button.dataset.target;
        const checkbox = targetId ? document.getElementById(targetId) : null;
        if (!checkbox) return;

        const card = button.closest('.image-card');

        const updateState = () => {
            const marked = checkbox.checked;
            if (card) {
                card.classList.toggle('is-marked', marked);
            }
            button.textContent = marked ? 'Undo remove' : 'Remove image';
            button.setAttribute('aria-pressed', marked ? 'true' : 'false');
        };

        updateState();

        button.addEventListener('click', () => {
            if (!checkbox.checked) {
                const confirmed = window.confirm('Remove this image? It will be deleted after you save.');
                if (!confirmed) return;
                checkbox.checked = true;
            } else {
                checkbox.checked = false;
            }
            updateState();
        });
    });
};

const initRichEditors = () => {
    const editors = document.querySelectorAll('[data-rich-editor]');
    if (!editors.length) return;

    const exec = (command, value = null) => {
        document.execCommand('styleWithCSS', false, true);
        document.execCommand(command, false, value);
    };

    editors.forEach((wrapper) => {
        const area = wrapper.querySelector('[data-rich-editor-area]');
        const input = wrapper.querySelector('[data-rich-input]');
        const toolbar = wrapper.querySelector('.rich-toolbar');
        if (!area || !input || !toolbar) return;

        let savedRange = null;

        const saveSelection = () => {
            const selection = window.getSelection();
            if (!selection || selection.rangeCount === 0) return;
            const range = selection.getRangeAt(0);
            if (area.contains(range.commonAncestorContainer)) {
                savedRange = range;
            }
        };

        const restoreSelection = () => {
            if (!savedRange) return;
            const selection = window.getSelection();
            if (!selection) return;
            selection.removeAllRanges();
            selection.addRange(savedRange);
        };

        const syncInput = () => {
            input.value = area.innerHTML;
        };

        toolbar.addEventListener('mousedown', (event) => {
            if (event.target.closest('button[data-command]')) {
                event.preventDefault();
            }
        });

        toolbar.addEventListener('click', (event) => {
            const button = event.target.closest('button[data-command]');
            if (!button) return;

            const command = button.dataset.command;
            area.focus();
            restoreSelection();

            if (command === 'createLink') {
                const url = window.prompt('Enter a URL');
                if (!url) return;
                exec(command, url);
                syncInput();
                return;
            }

            exec(command);
            syncInput();
        });

        toolbar.addEventListener('change', (event) => {
            const control = event.target;
            if (!control.matches('[data-command]')) return;
            if (!control.value) return;
            area.focus();
            restoreSelection();
            exec(control.dataset.command, control.value);
            syncInput();
        });

        area.addEventListener('input', syncInput);
        area.addEventListener('keyup', saveSelection);
        area.addEventListener('mouseup', saveSelection);

        const form = wrapper.closest('form');
        if (form) {
            form.addEventListener('submit', syncInput);
        }

        syncInput();
    });
};

window.addEventListener('DOMContentLoaded', () => {
    initAdminThemeToggle();
    initImageDeleteButtons();
    initRichEditors();
});
