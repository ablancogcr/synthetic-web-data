{% test non_negative(model, column_name) %}
select *
from {{ model }}
where {{ column_name }} < 0
{% endtest %}

{% test between_zero_and_one(model, column_name) %}
select *
from {{ model }}
where {{ column_name }} < 0
   or {{ column_name }} > 1
{% endtest %}

{% test less_than_or_equal_to(model, column_name, compare_column) %}
select *
from {{ model }}
where {{ column_name }} > {{ compare_column }}
{% endtest %}
