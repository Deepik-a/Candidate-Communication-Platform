from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0003_message_failure_category'),
    ]

    operations = [
        migrations.CreateModel(
            name='MessageTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('content', models.TextField()),
                ('channel', models.CharField(blank=True, choices=[('sms', 'SMS'), ('whatsapp', 'WhatsApp'), ('email', 'Email')], default='', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Message Template',
                'verbose_name_plural': 'Message Templates',
                'db_table': 'message_templates',
                'ordering': ['-updated_at', '-id'],
            },
        ),
        migrations.AddField(
            model_name='message',
            name='retry_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='message',
            name='scheduled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='message',
            name='template',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='messages',
                to='communications.messagetemplate',
            ),
        ),
        migrations.AlterField(
            model_name='message',
            name='status',
            field=models.CharField(
                choices=[
                    ('scheduled', 'Scheduled'),
                    ('pending', 'Pending'),
                    ('sent', 'Sent'),
                    ('delivered', 'Delivered'),
                    ('read', 'Read'),
                    ('failed', 'Failed'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
    ]
