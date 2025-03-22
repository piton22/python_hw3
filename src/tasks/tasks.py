from celery import shared_task
from sqlalchemy import create_engine, update, and_, or_, func
from sqlalchemy.orm import sessionmaker
from src.models import Link, Base
from src.config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER, REDIS_HOST, REDIS_PORT
from datetime import datetime, timedelta, timezone
import redis

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

@shared_task
def check_and_deactivate_links():
    session = Session()
    try:
        now = datetime.utcnow() + timedelta(hours=3)
        three_days_ago = now - timedelta(days=3)

        condition = and_(
            Link.deleted == False,
            or_(
                Link.expires_at < now,
                or_(
                    Link.last_usage < three_days_ago,
                    and_(
                        Link.last_usage.is_(None),
                        Link.created_at < three_days_ago
                    )
                )
            )
        )

        stmt = update(Link).where(condition).values(deleted=True)
        session.execute(stmt)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


@shared_task
def update_link_stats():
    redis_conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    session = Session()
    
    try:
        # Получаем все ключи статистики
        stats_keys = redis_conn.keys("link_stats:*")
        
        for key in stats_keys:
            short_code = key.decode().split(":")[1]
            stats = redis_conn.hgetall(key)
            
            if not stats:
                continue

            hits = int(stats.get(b'hits', 0))
            last_used_str = stats.get(b'last_used')
            last_used = datetime.fromisoformat(last_used_str.decode()) if last_used_str else None

            if hits > 0 and last_used:
                # Обновляем БД
                session.execute(
                    update(Link)
                    .where(Link.short == short_code)
                    .values(
                        cnt_usage=Link.cnt_usage + hits,
                        last_usage=func.greatest(Link.last_usage, last_used)
                    )
                )
                redis_conn.delete(key)

        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
        redis_conn.close()