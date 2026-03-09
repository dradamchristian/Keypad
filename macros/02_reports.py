from adafruit_hid.keycode import Keycode

app = {
    'name': 'Reports',
    'macros': [
        (0x009966, 'Duo', [
            'The sections show duodenal mucosa with normal villous architecture, there is no increase in intraepithelial lymphocytes. The appearances are within normal limits.'
        ]),

        (0x009966, 'Rec Gst', [
            'Antral gastric mucosa with features of a reactive gastropathy. There is no dysplasia or malignancy, there is no intestinal metaplasia and H pylori are not seen.'
        ]),

        (0x009966, 'NLB', [
            'The sections show large bowel mucosa within normal limits, there is no evidence of microscopic colitis.'
        ]),

        (0x009966, 'No evid ', [
            'There is no evidence of dysplasia or malignancy.'
        ]),

        (0x9966CC, 'Biom', [
            {'bio_wizard': True}
        ]),

        # Chooser for differentiation
        (0xCC6600, 'Cln Ca', [
            {'choose': {
                'title': 'Differentiation',
                'template': 'Colonic mucosa infiltrated by {grade} differentiated adenocarcinoma, MMR to follow.',
                'options': ['well', 'moderately', 'poorly']
            }}
        ]),

        # Multi-step chooser: grade + type + excision
        (0x3399FF, 'Adenoma ', [
            {'choose_multi': {
                'title': 'Adenoma report',
                'template': 'The sections show a {grade} grade {type} adenoma, {excision}.',
                'fields': [
                    {'name': 'grade',   'label': 'Grade',   'options': ['low', 'high']},
                    {'name': 'type',    'label': 'Type',    'options': ['tubular', 'tubulovillous', 'villous']},
                    {'name': 'excision','label': 'Excision','options': ['completely excised', 'excision cannot be guaranteed']}
                ]
            }}
        ]),

        (0x004488, 'Ex Work ', [
            {'extra_work_email': True}
        ]),
    ]
}
