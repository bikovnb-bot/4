from django.forms.widgets import SelectMultiple
from django.utils.safestring import mark_safe

class GroupedSelectMultiple(SelectMultiple):
    """Виджет для выбора прав, сгруппированных по приложениям."""
    def __init__(self, grouped_choices, attrs=None):
        self.grouped_choices = grouped_choices  # [(group_label, [(value, label), ...]), ...]
        super().__init__(attrs=attrs)

    def optgroups(self, name, value, attrs=None):
        """Переопределяем для генерации <optgroup>."""
        groups = []
        for group_label, choices in self.grouped_choices:
            group = {
                'name': group_label,
                'options': [
                    {
                        'name': name,
                        'value': str(choice_value),
                        'label': str(choice_label),
                        'selected': str(choice_value) in value,
                        'attrs': {},
                    }
                    for choice_value, choice_label in choices
                ]
            }
            groups.append(group)
        return groups