const initAdminThemeToggle = () => {
    const toggle = document.querySelector('[data-theme-toggle]');
    if (!toggle) return;

    const storageKey = 'admin-theme';
    const apply = (mode) => {
        const isDark = mode === 'dark';
        document.body.classList.toggle('theme-dark', isDark);
        toggle.setAttribute('aria-pressed', isDark ? 'true' : 'false');
        toggle.setAttribute('aria-label', isDark ? 'Switch to light theme' : 'Switch to dark theme');
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

const initCkeditor = () => {
    const fields = document.querySelectorAll('[data-ckeditor]');
    if (!fields.length) return;

    const warnings = document.querySelectorAll('[data-ckeditor-warning]');
    const showWarning = () => {
        warnings.forEach((warning) => warning.classList.add('is-visible'));
    };

    if (!window.ClassicEditor) {
        console.warn('CKEditor assets missing. Place ckeditor5.js in static/vendor/ckeditor/.');
        showWarning();
        return;
    }

    const pluginNames = new Set(
        (ClassicEditor.builtinPlugins || [])
            .map((plugin) => plugin.pluginName)
            .filter((name) => name)
    );

    const pluginMap = {
        heading: 'Heading',
        bold: 'Bold',
        italic: 'Italic',
        underline: 'Underline',
        fontFamily: 'FontFamily',
        fontSize: 'FontSize',
        fontColor: 'FontColor',
        fontBackgroundColor: 'FontBackgroundColor',
        link: 'Link',
        bulletedList: 'List',
        numberedList: 'List',
        undo: 'Essentials',
        redo: 'Essentials',
    };

    const buildToolbar = () => {
        const groups = [
            ['heading'],
            [
                'bold',
                'italic',
                'underline',
                'fontFamily',
                'fontSize',
                'fontColor',
                'fontBackgroundColor',
            ],
            ['link', 'bulletedList', 'numberedList'],
            ['undo', 'redo'],
        ];

        const items = [];

        groups.forEach((group) => {
            const filtered = group.filter((item) => pluginNames.has(pluginMap[item]));
            if (!filtered.length) return;
            if (items.length) items.push('|');
            items.push(...filtered);
        });

        return items;
    };

    const toolbarItems = buildToolbar();

    fields.forEach((field) => {
        ClassicEditor.create(
            field,
            toolbarItems.length
                ? {
                      toolbar: {
                          items: toolbarItems,
                          shouldNotGroupWhenFull: true,
                      },
                      link: {
                          defaultProtocol: 'https://',
                          addTargetToExternalLinks: true,
                      },
                  }
                : {}
        )
            .then((editor) => {
                const form = field.closest('form');
                if (form) {
                    form.addEventListener('submit', () => {
                        field.value = editor.getData();
                    });
                }
            })
            .catch((error) => {
                console.error('Failed to initialize CKEditor.', error);
                showWarning();
            });
    });
};

window.addEventListener('DOMContentLoaded', () => {
    initAdminThemeToggle();
    initImageDeleteButtons();
    initCkeditor();
});
