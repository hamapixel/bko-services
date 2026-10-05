from django.db import migrations


PAID_PLANS = [
    {
        "code": "mensuel-essentiel",
        "name": "Essentiel",
        "description": (
            "Pour démarrer : demandes normales dans vos métiers et zones "
            "d’intervention. Une intervention en cours à la fois."
        ),
        "price_xof": 2000,
        "duration_days": 30,
        "can_receive_requests": True,
        "can_receive_urgent_requests": False,
        "max_active_jobs": 1,
        "is_active": False,
        "display_order": 10,
    },
    {
        "code": "mensuel-plus",
        "name": "Plus",
        "description": (
            "Pour les prestataires actifs : demandes normales et urgentes dans "
            "vos métiers et zones d’intervention. Jusqu’à trois interventions "
            "en cours à la fois."
        ),
        "price_xof": 4000,
        "duration_days": 30,
        "can_receive_requests": True,
        "can_receive_urgent_requests": True,
        "max_active_jobs": 3,
        "is_active": False,
        "display_order": 20,
    },
    {
        "code": "mensuel-pro",
        "name": "Pro",
        "description": (
            "Pour les prestataires très actifs ou les équipes : demandes "
            "normales et urgentes dans vos métiers et zones d’intervention, "
            "sans limite d’interventions simultanées."
        ),
        "price_xof": 7500,
        "duration_days": 30,
        "can_receive_requests": True,
        "can_receive_urgent_requests": True,
        "max_active_jobs": None,
        "is_active": False,
        "display_order": 30,
    },
]


def seed_paid_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model("subscriptions", "SubscriptionPlan")

    for plan in PAID_PLANS:
        code = plan["code"]
        defaults = {key: value for key, value in plan.items() if key != "code"}
        existing, created = SubscriptionPlan.objects.get_or_create(
            code=code,
            defaults=defaults,
        )

        # If an earlier UI action only created an unpublished zero-price draft,
        # promote that draft to the launch defaults. Never overwrite a plan that
        # an administrator has already priced or published.
        if not created and existing.price_xof == 0 and not existing.is_active:
            for field, value in defaults.items():
                setattr(existing, field, value)
            existing.save(update_fields=list(defaults))


def noop_reverse(apps, schema_editor):
    # Keep business data on rollback; subscriptions may already reference plans.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0004_free_trial_used_at"),
    ]

    operations = [
        migrations.RunPython(seed_paid_plans, noop_reverse),
    ]
